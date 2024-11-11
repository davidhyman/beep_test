from collections import namedtuple

import pydub

from pydub.generators import Sine, Triangle, Square, Sawtooth
from csv import DictReader

# from gtts import gTTS
# tts = gTTS("level 1")
# tts.save("L1.mp3")
# L1 = pydub.AudioSegment.from_mp3("./L1.mp3")

lap = namedtuple("lap", "level, length, start, recover")
laps = []
with open("beep bleep test - Sheet1 (1).csv") as csvfile:
    reader = DictReader(csvfile)
    # if level isn't repeated, take the previous value
    level_previous = 0
    for row in reader:
        level = row["level"]
        if level:
            level_previous = level
        else:
            level = level_previous
        laps.append(lap(level=level, length=row["length"], start=row["start"], recover=row["recover"]))

# print(laps)

ms = 1000
# primer = pydub.AudioSegment.from_wav("./beep-07a.wav")
# starter = pydub.AudioSegment.from_wav("./beep-02.wav")
primer = Sine(900).to_audio_segment(duration=0.1*ms).fade_in(10).fade_out(10)
starter = Sawtooth(1200).to_audio_segment(duration=0.7*ms).fade_in(10).fade_out(10)
short_silence = pydub.AudioSegment.silent(duration=0.5*ms)
second_silence = pydub.AudioSegment.silent(duration=1*ms)
# silence = pydub.AudioSegment.from_mp3("./5-seconds-of-silence.mp3")
# silence = pydub.AudioSegment(sample_width=1.0, channels=1, frame_rate=44000, data=bytearray(44000 * [0]))

beep = primer + short_silence + primer + short_silence + starter
print(beep.duration_seconds)
song = second_silence + beep

# to avoid accumulating floating point errors
# we should start with a silent buffer at ~15 minutes long
# and overlay our beep at every interval -beep.duration_seconds


song.apply_gain(-2)
from pydub.playback import play
play(song)




# song.export("mashup.mp3", format="mp3")
