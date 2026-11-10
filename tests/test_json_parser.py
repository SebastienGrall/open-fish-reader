from pathlib import Path

from open_fish_reader.indexing.json_parser import parse_video_part_json


def test_parse_json():
    p = Path(__file__).parent / "fixtures" / "valid_video_part.json"
    part = parse_video_part_json(p)
    assert part.station_name == "Poses RG OFC"
    assert part.video_start_time.utcoffset().total_seconds() == 3600
