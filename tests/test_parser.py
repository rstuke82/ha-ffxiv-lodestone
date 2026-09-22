"""Parser unit tests."""

from custom_components.ffxiv_lodestone.models import JobData
from custom_components.ffxiv_lodestone.parser import (
    parse_achievement_summary,
    parse_class_jobs,
    parse_collection_count,
    parse_profile,
    resolve_current_job,
    slugify,
)


def test_slugify_character_name():
    assert slugify("First Surname") == "first_surname"


def test_parse_class_jobs_and_progression():
    html = """
    <html><body>
      <div>100</div><div>Paladin</div><div>-- / --</div>
      <div>70</div><div>Blue Mage</div><div>1,304,786 / 2,923,000</div>

      <div>60</div><div>Elemental Level</div><div>-- / --</div>
      <div>25</div><div>Resistance Rank</div><div>-- / --</div>
      <div>20</div><div>Knowledge Level</div><div>3,000 / 9,000</div>
    </body></html>
    """
    jobs, progression = parse_class_jobs(html)
    assert jobs["paladin"].level == 100
    assert jobs["blue_mage"].current_xp == 1304786
    assert progression["eureka"].level == 60
    assert progression["bozja"].level == 25
    assert progression["occult_crescent"].level == 20
    assert progression["occult_crescent"].current == 3000
    assert progression["occult_crescent"].maximum == 9000


def test_achievement_current_layout():
    html = """
    <html><body>
      <h3>Achievements</h3>
      <div>13015</div>
      <a>Achievement History</a>
      <div>1505 Total</div>
      <a>Items achievement "Example Achievement" earned!</a>
    </body></html>
    """
    data = parse_achievement_summary(html)
    assert data.points == 13015
    assert data.count == 1505
    assert data.latest_name == "Example Achievement"


def test_collection_total():
    assert parse_collection_count("<h3>Mounts</h3><p>Total: 116</p>") == 116


def test_profile_job_local_block_wins():
    html = """
    <html><body>
      <div class="frame__chara__name">Example Character</div>
      <div>Paladin</div>
      <section class="profile-current-job">
        <img alt="Sage">
        <span>Sage</span>
        <div>LEVEL 100</div>
        <div>Mind | 6208</div>
      </section>
    </body></html>
    """
    data = parse_profile("123", html)
    assert data.current_job == "Sage"


def test_resolve_text_name_before_icon():
    jobs = {
        "paladin": JobData(name="Paladin", slug="paladin", icon_url="same.png"),
        "sage": JobData(name="Sage", slug="sage", icon_url="other.png"),
    }
    assert resolve_current_job("Sage", "same.png", jobs) == "Sage"


def test_profile_job_icon_is_first_image_after_level():
    html = """
    <html><body>
      <div class="frame__chara__name">Example Character</div>
      <img src="https://example.invalid/gear.png">
      <div>LEVEL 100</div>
      <img src="https://lds-img.finalfantasyxiv.com/job-sage.png">
      <div>Mind | 6208</div>
    </body></html>
    """
    data = parse_profile("123", html)
    displayed = data.jobs["_displayed_profile"]
    assert displayed.icon_url == "https://lds-img.finalfantasyxiv.com/job-sage.png"


def test_clean_icon_filename_convention():
    # The transparent icon repository uses normalized names without spaces.
    assert "White Mage".lower().replace(" ", "") == "whitemage"
    assert "Dark Knight".lower().replace(" ", "") == "darkknight"
