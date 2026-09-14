"""The template language: what a token renders to, and which number comes next."""
from comfyui_sg import naming


def test_a_token_with_no_value_drops_out_with_its_separator():
    """A Version with no Task renders the entity alone, not `sh010_`."""
    assert naming.render(naming.DEFAULT_ROOT_TEMPLATE, {"entity": "sh010"}) == "sh010"


def test_an_optional_block_vanishes_whole():
    values = {"entity": "sh010"}
    assert naming.render("{entity}[_{sg_task.Task.content}]_v{version:03d}", values, 3) \
        == "sh010_v003"


def test_an_optional_block_survives_when_its_field_has_a_value():
    values = {"entity": "sh010", "sg_task.Task.content": "comp"}
    assert naming.render("{entity}[_{sg_task.Task.content}]_v{version:03d}", values, 3) \
        == "sh010_comp_v003"


def test_printf_padding_is_the_version_a_td_typed():
    assert naming.normalise_template("plate_v%04d") == "plate_v{version:04d}"
    assert naming.render("plate_v%04d", {}, 7) == "plate_v0007"


def test_a_dotted_path_is_one_key_not_an_attribute_walk():
    assert naming.render("{entity.Shot.code}_v{version:03d}",
                         {"entity.Shot.code": "sh010"}, 1) == "sh010_v001"


def test_the_next_version_counts_only_this_streams_codes():
    codes = ["sh010_comp_v001", "sh010_comp_v002", "sh020_comp_v009", "sh010_matte_v004"]
    assert naming.next_version(codes, naming.DEFAULT_TEMPLATE, {"root_name": "sh010_comp"}) == 3


def test_the_matcher_accepts_the_per_frame_suffix():
    """A batch publishes one Version per frame and appends `_01`; a re-run must not restart at 1."""
    codes = ["sh010_comp_v002_01", "sh010_comp_v002_02"]
    assert naming.next_version(codes, naming.DEFAULT_TEMPLATE, {"root_name": "sh010_comp"}) == 3


def test_the_next_number_is_the_highest_plus_one():
    assert naming.next_number([1, 3, None, "7"]) == 4
    assert naming.next_number([]) == 1


def test_parse_reads_the_version_as_a_number():
    got = naming.parse("sh010_comp_v012", r"(?P<name>.+)_v(?P<version>\d+)$")
    assert got["version"] == 12
    assert naming.parse("nothing_like_it", r"(?P<version>\d+)$") is None
