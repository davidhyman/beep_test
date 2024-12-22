import dataclasses
import sys
from pathlib import Path
from typing import List

import pydub
from pydub import AudioSegment

from pydub.generators import Sine, Sawtooth
from csv import DictReader

import pyttsx3

ms = 1000
TTS_CACHE = True
speakers = Path("speakers")


def demo_voices():
    engine = pyttsx3.init()
    for indx, voice in enumerate(engine.getProperty('voices')):
        print(f"this is voice {indx}: {voice}")
        engine.setProperty("voice", voice.id)
        engine.say(f"this is voice {indx}")
        engine.runAndWait()


def tts(text: str, filepath: Path, cache: bool):
    if filepath.exists() and cache:
        return
    print("new tts for ", text, filepath)
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.save_to_file(text, str(filepath))
    engine.runAndWait()


def number_to_tts(number: int, cache: bool):
    level_name = str(number)
    if number >= 10:
        numeric = " ".join([n for n in list(level_name)])
        level_name = f"{level_name}. {numeric}"
    text = f"next swim - {level_name}"
    filename = speakers / f"speaker_{number}.mp3"
    tts(text, filename, cache)
    completed_filename = speakers / f"speaker_completed_{number}.mp3"
    tts(f'completed {level_name}', completed_filename, cache)


def s_to_m(secs: float) -> str:
    mins = int(secs / 60)
    secs = secs - 60 * mins
    return f"{mins}:{secs:0.2f}"


def m_to_s(text: str) -> float:
    m, s = text.split(":")
    return int(m) * 60 + float(s)


@dataclasses.dataclass
class Interval:
    interval: int
    level: int
    start_text: str
    start_seconds: int
    duration_seconds: int
    is_new_level: bool

    def announce_lap(self) -> AudioSegment:
        """the length / interval number"""
        # ensure we have the announcer
        number_to_tts(self.interval, cache=TTS_CACHE)
        return pydub.AudioSegment.from_wav(speakers / f"speaker_{self.interval}.mp3")

    def pre_beep(self, pre_sequence: AudioSegment):
        """everything before the beep"""
        announcements = (
            self.announce_lap()
            + pydub.AudioSegment.silent(duration=0.5 * ms)
            + pre_sequence
        )
        if self.is_new_level:
            announcements = (
                self.announce_level()
                + pydub.AudioSegment.silent(duration=0.5 * ms)
                + announcements
            )
        return announcements

    def announce_level(self):
        filepath = speakers / f"level_{self.level}_{self.duration_seconds}.mp3"
        tts(f"level {self.level}, {self.duration_seconds} seconds", filepath=filepath, cache=TTS_CACHE)
        return pydub.AudioSegment.from_wav(filepath)

    def beep_sequence(self, beep_sequence: AudioSegment) -> AudioSegment:
        """everything from 'start' onwards"""
        return beep_sequence


def load_csv_intervals(filepath: Path) -> List[Interval]:
    intervals = []
    with open(filepath) as csvfile:
        reader = DictReader(csvfile)
        # if level isn't repeated, take the previous value
        seconds = 0
        level_previous = 0
        level_changed_from = 0
        for row in reader:
            level = row["level"]
            if level:
                level_previous = level
            else:
                level = level_previous

            level_change = False
            if level != level_changed_from:
                level_change = True
                level_changed_from = level

            duration = int(float(row["recovery"].split(":")[1]))

            intervals.append(Interval(
                interval=int(row["length"]),
                level=int(level),
                start_text=row["start"],
                start_seconds=seconds,
                duration_seconds=duration,
                is_new_level=level_change,
            ))

            # warning! the input CSV is broken
            # assert seconds == m_to_s(row["start"]), f"{int(row["length"])} doesnt add up {seconds} {m_to_s(row["start"])}"

            seconds += duration

    return intervals


def fake_intervals() -> List[Interval]:
    return [
        Interval(
            level=6,
            is_new_level=False,
            start_seconds=1231,
            start_text="5:30",
            duration_seconds=10,
            interval=17,
        ),
        Interval(
            level=7,
            is_new_level=True,
            start_seconds=14323,
            start_text="5:30",
            duration_seconds=15,
            interval=23,
        ),
        Interval(
            level=7,
            is_new_level=True,
            start_seconds=14323,
            start_text="5:30",
            duration_seconds=13,
            interval=69,
        ),
    ]


def silence(secs: float) -> pydub.AudioSegment:
    return pydub.AudioSegment.silent(duration=secs * ms)


def build_track(intervals) -> AudioSegment:
    print(intervals)

    primer = Sine(900).to_audio_segment(duration=0.1 * ms).fade_in(10).fade_out(10)
    gap = pydub.AudioSegment.silent(duration=0.7 * ms)
    pre_sequence = primer + gap + primer + gap
    starter = Sawtooth(1200).to_audio_segment(duration=1.5 * ms).fade_in(10).fade_out(10)

    total_duration_seconds = sum(interval.duration_seconds for interval in intervals)
    print(f"building audio for {total_duration_seconds} seconds (plus misc)")

    full_sequence = silence(0)
    initial_gap = 10
    remaining_in_interval = initial_gap
    cumulative_start = 0
    for interval in intervals:
        pre = interval.pre_beep(pre_sequence)
        post = interval.beep_sequence(starter)

        sleep = remaining_in_interval - pre.duration_seconds

        if sleep <= 0:
            raise ValueError(
                f"interval too short: need: {sleep:.02f}, have {remaining_in_interval:.02f}, pre: {pre.duration_seconds:.02f}, start: {cumulative_start} {s_to_m(cumulative_start)}"
            )

        swim_gap = silence(sleep)

        expect = cumulative_start + initial_gap
        difference = expect - (full_sequence + swim_gap + pre).duration_seconds

        # fix the timings to ensure we always align as close
        # as possible to true timing boundaries
        if difference > 0:
            swim_gap += silence(difference)

        full_sequence += swim_gap + pre

        print(
            f"adding level {interval.level} ({interval.duration_seconds}s) beep {interval.interval} at {full_sequence.duration_seconds} "
            f"expected abs {interval.start_seconds + initial_gap} "
            f"(rel {cumulative_start + initial_gap}) "
            f"equivalent input: {interval.start_text} vs {s_to_m(full_sequence.duration_seconds - initial_gap)}")
        full_sequence += post

        remaining_in_interval = interval.duration_seconds
        remaining_in_interval -= post.duration_seconds
        cumulative_start += interval.duration_seconds
    return full_sequence


def get_version_audio(version_name: str) -> AudioSegment:
    safe_name = version_name.replace(" ", "_")
    version_file = speakers / f"{safe_name}.mp3"
    tts(f"completed {version_name}", filepath=version_file, cache=True)
    return pydub.AudioSegment.from_wav(version_file)

def run(input_filepath: Path, version_name: str) -> AudioSegment:
    speakers.mkdir(exist_ok=True, parents=True)

    intervals = load_csv_intervals(input_filepath)[:45]
    full_sequence = build_track(intervals)
    full_sequence += silence(1) + get_version_audio(version_name)
    full_sequence.apply_gain(-2)
    fmt = "mp3"
    safe_name = version_name.replace(" ", "_")
    full_sequence.export(f"{safe_name}.{fmt}", format=fmt)
    return full_sequence


def booleanise(s:str) -> bool:
    lower = s.lower()
    if "yes".startswith(lower) or "true" in lower or lower=="1":
        return True
    if "no".startswith(lower) or "false" in lower or lower == "0":
        return False
    raise ValueError(f"what does '{s}' mean? its needs to be boolean")


def run_cli(do_voice_demo, play_track, input_filepath, version_name):
    if booleanise(do_voice_demo):
        if play_track:
            from pydub.playback import play
            play(get_version_audio(version_name))
        demo_voices()
        return
    play_track = booleanise(play_track)

    song = run(Path(input_filepath), version_name)

    if play_track:
        from pydub.playback import play
        print("playing ... ctrl-c to cancel")
        play(song)


__name__ == "__main__" and run_cli(*sys.argv[1:])
