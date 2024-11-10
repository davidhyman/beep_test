import pydub
from pydub.generators import Sine, Triangle, Square, Sawtooth

ms = 1000
# primer = pydub.AudioSegment.from_wav("./beep-07a.wav")
# starter = pydub.AudioSegment.from_wav("./beep-02.wav")
primer = Sine(900).to_audio_segment(duration=0.1*ms).fade_in(10).fade_out(10)
starter = Sawtooth(1200).to_audio_segment(duration=0.7*ms).fade_in(10).fade_out(10)
short_silence = pydub.AudioSegment.silent(duration=0.5*ms)
second_silence = pydub.AudioSegment.silent(duration=1*ms)
# silence = pydub.AudioSegment.from_mp3("./5-seconds-of-silence.mp3")
# silence = pydub.AudioSegment(sample_width=1.0, channels=1, frame_rate=44000, data=bytearray(44000 * [0]))

song = second_silence + primer + short_silence + primer + short_silence + starter
song.apply_gain(-2)
from pydub.playback import play
play(song)

# song.export("mashup.mp3", format="mp3")
