from flask import Flask, render_template, redirect, url_for
from datetime import datetime
import pandas as pd
from miditime.miditime import MIDITime
import random
import sys
import mido
from mido import Message, MidiFile, MidiTrack, MAX_PITCHWHEEL, MetaMessage
import numpy as np
import math
from music21 import midi
from sodapy import Socrata
from flask import request
import json
import subprocess
import os.path

app = Flask(__name__)

def calculate_key(midi_note_number, key_type):
    '''
    midi_note_number: based on the MIDI standard
    key_type options:
        major
        minor_natural
        major_pentatonic
    '''
    key = [midi_note_number]
    
    if key_type.lower() == 'major':
        # Major scales are formed by taking the follwing steps = Whole, Whole, Half, Whole, Whole, Whole, Half
        # Where whole steps are two semtitones and Half are one semitone. 
        # Increasing the midi number means an increase of one semitone
        steps = ['W','W','H','W','W','W','H']
        for i in range(len(steps)):
            # If we need to take a whole step, increase by two, otherwise by one
            if steps[i] == 'W':
                midi_note_number = midi_note_number + 2
                key.append(midi_note_number)
            else:
                midi_note_number = midi_note_number + 1
                key.append(midi_note_number)
    elif key_type.lower() == 'minor_natural':
        # Minor scales are formed by taking the follwing steps = Whole, Whole, Half, Whole, Whole, Whole, Half
        # Whole, Half, Whole, Whole, Half, Whole, Whole
        steps = ['W','H', 'W', 'W', 'H' ,'W', 'W']
        for i in range(len(steps)):
            # If we need to take a whole step, increase by two, otherwise by one
            if steps[i] == 'W':
                midi_note_number = midi_note_number + 2
                key.append(midi_note_number)
            else:
                midi_note_number = midi_note_number + 1
                key.append(midi_note_number)   
    elif key_type.lower() == 'major_pentatonic':
        # Major scales are formed by taking the follwing steps = Whole, Whole, Half, Whole, Whole, Whole, Half
        # Where whole steps are two semtitones and Half are one semitone. 
        # Increasing the midi number means an increase of one semitone
        steps = ['W','W','H','W','W','W','H']
        for i in range(len(steps)):
            # If we need to take a whole step, increase by two, otherwise by one
            if steps[i] == 'W':
                midi_note_number = midi_note_number + 2
                key.append(midi_note_number)
            else:
                midi_note_number = midi_note_number + 1
                key.append(midi_note_number)
            # only select 1,2,3,5,7 degrees (due to 9 indexing we substract one)
        key = [key[i] for i in [0,1,2,4,6]]

    return key

def calculate_times(value):
	ppm_levels = {'good':33,'fair': 66,'poor': 100,'very poor': 150, 'hazardous': 200}
	if value < ppm_levels['good']:
	    note_time = 2
	elif value < ppm_levels['fair']:
	    note_time = 4
	elif value < ppm_levels['poor']:
	    note_time = 8
	elif value  < ppm_levels['very poor']:
	    note_time = 32
	elif value > ppm_levels['very poor']:
	    note_time = 64
	return note_time

def calculate_months(results_df):
    unique_months = results_df['yearmonth'].unique()
    ordered_months = np.sort(unique_months).tolist()
    months_string = ",".join(str(x) for x in ordered_months)
    return ordered_months





@app.route('/')
def song_player_screen():
    datos, audio_name, months = create_song()
    return render_template('index.html', audio_file = audio_name, months = months)



def create_song():
    
    # Unauthenticated client only works with public data sets. Note 'None'
    # in place of application token, and no username or password:
    client = Socrata("www.data.act.gov.au", None)

    # Example authenticated client (needed for non-public datasets):
    # client = Socrata(www.data.act.gov.au,
    #                  MyAppToken,
    #                  userame="user@example.com",
    #                  password="AFakePassword")

    # First 2000 results, returned as JSON from API / converted to Python list of
    # dictionaries by sodapy.
    results = client.get("i5w3-megw", limit=2000)

    # Convert to pandas DataFrame
    results_df = pd.DataFrame.from_records(results)
    results_df['date'] = list(map(lambda d: str(d.split('T')[0]), results_df['datetime']))
    results_df['yearmonth'] = list(map(lambda d: str(d.split('-')[0]) + '-' + str(d.split('-')[1]), results_df['date']))

    air = results_df.dropna()
    air.aqi_co = air.aqi_co.astype(int) 
    air.aqi_no2 = air.aqi_no2.astype(int) 
    air.aqi_o3_1hr = air.aqi_o3_1hr.astype(int) 
    air.aqi_o3_4hr = air.aqi_o3_4hr.astype(int) 
    air.aqi_pm10 = air.aqi_pm10.astype(int) 
    air.aqi_pm2_5 = air.aqi_pm2_5.astype(int)
    air.aqi_pm2_5 = air.aqi_pm2_5.astype(int)
    air.aqi_site = air.aqi_site.astype(int)

    air_monthly_mean = air.groupby(by='yearmonth').mean()
    air_monthly_mean.reset_index(inplace=True)

    air_monthly_mean = air_monthly_mean[['aqi_co','aqi_no2','aqi_o3_4hr','aqi_pm10','aqi_pm2_5']]

    ppm_levels = {'good':33,'fair': 66,'poor': 100,'very poor': 150, 'hazardous': 200}

    key = calculate_key(65,'major_pentatonic')

    midi_file = MidiFile()
    i = 0
    iters = 0

    for column in air_monthly_mean:
        track = MidiTrack()
        midi_file.tracks.append(track)
        # calculate how frequently you will insert it 
        # determine what note it is going to be assigned
        for value in air_monthly_mean[column]:
            # determine how many you will insert, which is the number provided by calculate
            times = calculate_times(value)     
            for insert in range(times):
                # if we want to insert it four times, we need to space it such that it fits in one measure, we do that by 
                # dividing 480, the number of ticks per measure over the number of times
                track.append(Message('note_on', note=key[i], velocity=40, time=int(960/times)))
                track.append(Message('note_off', note=key[i], velocity=40, time=int(1100/times)))
                track.append(Message('program_change', program=12 + i))

        
        track.append(MetaMessage('set_tempo',tempo=1000000))

        # Create a file for each sound
        midi_individual = MidiFile()
        track_individual = MidiTrack()
        midi_individual.tracks.append(track_individual)

        track_individual.append(Message('program_change', program=12+i))
        track_individual.append(Message('note_on', note=key[i], velocity=40, time=1))
        track_individual.append(Message('note_off', note=key[i], velocity=40, time=480))
        midi_individual_name = 'air' + str(i) + '.midi'
        midi_individual.save(midi_individual_name)
        wav_individual_name = 'static/air' + str(i) + '.wav'
        command_string = 'fluidsynth -ni static/Soundfonts/fluid-soundfont-3.1.2/FluidR3_GM.sf2 ' + midi_individual_name + ' -F ' + wav_individual_name + '  -r 44100'
   
        command_list = []
        for command  in command_string.split():
            command_list.append(command)
        #result = subprocess.run(command_list)

        i += 1




    midi_file.save('air.midi')   
    
    # we calculate the note time value. We will fill each measure (4 pulses) with each note time
    # 1/4 notes will be inserted four times
    # 1/8 notes will be inserted 8 times

    # 1/4 = good
    # 1/8 = fair
    # 1/16 = poor
    # 1/32 = very poor
    # 1/64 = hazardous  
    
    if os.path.isfile('./static/air.wav'):
        #delete_comm = subprocess.run(['rm','./static/air.wav'])
    else:
        print ("air.wav was not created yet")


    command_string = 'fluidsynth -ni static/Soundfonts/fluid-soundfont-3.1.2/FluidR3_GM.sf2 air.midi -F static/air.wav -r 44100'
    
    audio_name = 'air.wav'      
    command_list = []
    for i  in command_string.split():
        command_list.append(i)
    #result = subprocess.run(command_list)

    months = calculate_months(results_df)

    


    return air_monthly_mean, audio_name, months



