import subprocess

delete_comm = subprocess.run(['rm','air.wav'])
command_string = 'fluidsynth -ni static/Soundfonts/fluid-soundfont-3.1.2/FluidR3_GM.sf2 air.midi -F static/air.wav -r 44100'
command_string = 'fluidsynth -ni static/Soundfonts/fluid-soundfont-3.1.2/FluidR3_GM.sf2 air.midi -F static/air.wav -r 44100'

command_list = []
for i  in command_string.split():
	command_list.append(i)

print(command_list)

result = subprocess.run(command_list)