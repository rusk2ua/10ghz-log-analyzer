"""VHF contest support: bands, ADIF, contest detection and scoring."""

import os
import subprocess
import sys
from datetime import datetime

import pandas as pd
import pytest

import contests
import data_source as ds
from contests import ARRL_10_GHZ, ARRL_VHF_JAN, ARRL_VHF_JUN, ARRL_VHF_SEP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def log(rows):
    """DataFrame from (band, mode, date, time, mygrid, call, grid) tuples."""
    return pd.DataFrame([dict(zip(('band', 'mode', 'date', 'time', 'sourcegrid', 'call', 'grid'), r))
                         for r in rows])


# A small June 2026 rover log: two stops, a duplicate, a re-work after moving,
# a re-work of a rover after it moved, and a QSO outside the contest.
JUNE_ROVER = [
    ('50',   'PH', '2026-06-13', '1800', 'FN12', 'W2FU', 'FN13'),
    ('144',  'PH', '2026-06-13', '1801', 'FN12', 'W2FU', 'FN13'),
    ('902',  'PH', '2026-06-13', '1802', 'FN12', 'W2FU', 'FN13'),
    ('10G',  'CW', '2026-06-13', '1803', 'FN12', 'W2FU', 'FN13'),
    ('144',  'PH', '2026-06-13', '1804', 'FN12', 'W2FU', 'FN13'),       # duplicate
    ('144',  'PH', '2026-06-13', '1805', 'FN12', 'KF2MR/R', 'FN22'),
    ('144',  'PH', '2026-06-13', '1900', 'FN12', 'KF2MR/R', 'FN02'),    # rover moved: counts
    ('144',  'PH', '2026-06-14', '0100', 'FN13', 'W2FU', 'FN13'),       # I moved: counts
    ('222',  'FM', '2026-06-14', '0101', 'FN13', 'N2ZN', 'FN13'),
    ('144',  'PH', '2026-06-16', '1200', 'FN13', 'K2TER', 'FN13'),      # after the contest
]


def test_vhf_bands_map_from_every_spelling():
    for raw, display, code in [('50', '50 MHz', '50'), ('2m', '144 MHz', '144'),
                               ('1.2G', '1.2 GHz', '1.2G'), ('1296', '1.2 GHz', '1.2G'),
                               ('23cm', '1.2 GHz', '1.2G'), ('144205', '144 MHz', '144'),
                               ('3cm', '10 GHz', '10G'), ('24', '24 GHz', '24G'),
                               ('78', '78 GHz', '75G'), ('4mm', '78 GHz', '75G')]:
        assert ds.normalize_band(raw) == display
        assert ds.band_to_cabrillo(raw) == code


def test_ten_ghz_multipliers_unchanged_and_vhf_bands_score_zero():
    assert [ds.band_multiplier(b) for b in ('10', '24', '47', '78', '122', '134', '241')] == \
        [1, 2, 3, 4, 5, 5, 5]
    assert ds.band_multiplier('144') == 0
    assert ds.TEN_GHZ_BANDS[0] == '10 GHz'


def test_file_safe_call():
    assert ds.file_safe_call('k2ua/r') == 'K2UA-R'


@pytest.mark.parametrize('year, month, n, day', [
    (2026, 1, 3, 17), (2025, 1, 3, 18), (2026, 6, 2, 13), (2026, 9, 2, 12),
    (2026, 8, 3, 15), (2026, 9, 3, 19),
])
def test_nth_full_weekend(year, month, n, day):
    assert contests._nth_saturday(year, month, n).day == day


def test_contest_windows():
    jan = contests.CONTESTS[ARRL_VHF_JAN]
    assert jan.in_window(datetime(2025, 1, 18, 19, 0))
    assert jan.in_window(datetime(2025, 1, 20, 3, 59))
    assert not jan.in_window(datetime(2025, 1, 18, 18, 59))
    assert jan.in_window(datetime(2025, 1, 25, 20, 0))      # fourth weekend, if announced
    jun = contests.CONTESTS[ARRL_VHF_JUN]
    assert jun.in_window(datetime(2026, 6, 13, 18, 0))
    assert not jun.in_window(datetime(2026, 6, 15, 3, 0))


def test_january_doubles_the_upper_band_points():
    jan, jun = contests.CONTESTS[ARRL_VHF_JAN], contests.CONTESTS[ARRL_VHF_JUN]
    assert [jan.qso_points(b) for b in ('50', '144', '222', '432', '902', '1.2G', '2.3G', '10G', '24G')] == \
        [1, 1, 2, 2, 4, 4, 8, 8, 8]
    assert [jun.qso_points(b) for b in ('50', '144', '222', '432', '902', '1.2G', '2.3G', '10G', '24G')] == \
        [1, 1, 2, 2, 3, 3, 4, 4, 4]


def test_detect_from_header_then_dates():
    df = log(JUNE_ROVER)
    assert contests.detect_contest(df, {'CONTEST': 'ARRL-VHF-SEP'}).contest_id == ARRL_VHF_SEP
    found = contests.detect_contest(df, {})
    assert found.contest_id == ARRL_VHF_JUN and '9 of 10' in found.reason


def test_detect_ten_ghz_and_no_contest():
    ten = log([('10G', 'CW', '2026-08-15', '1200', 'FN12', 'W2FU', 'FN13')])
    assert contests.detect_contest(ten, {}).contest_id == ARRL_10_GHZ
    vhf_on_ten_weekend = log([('144', 'PH', '2026-08-15', '1200', 'FN12', 'W2FU', 'FN13')])
    assert contests.detect_contest(vhf_on_ten_weekend, {}).contest_id is None
    ten_on_vhf_weekend = log([('10G', 'CW', '2026-09-12', '1900', 'FN12', 'W2FU', 'FN13')])
    assert contests.detect_contest(ten_on_vhf_weekend, {}).contest_id is None
    home = log([('144', 'FT8', '2026-03-03', '1200', 'FN12', 'W2FU', 'FN13')])
    assert contests.detect_contest(home, {}).contest_id is None


def test_rover_score():
    r = contests.score_vhf(log(JUNE_ROVER), ARRL_VHF_JUN, 'R')
    # Counted: 50, 144, 902 (3), 10G (4), 144 KF2MR FN22, 144 KF2MR FN02,
    # 144 W2FU from FN13, 222 (2)
    assert r['qso_points'] == 1 + 1 + 3 + 4 + 1 + 1 + 1 + 2
    # band-grids: 50/FN13 144/FN13 144/FN22 144/FN02 902/FN13 10G/FN13 222/FN13
    assert r['band_grids'] == 7
    assert r['activated'] == ['FN12', 'FN13']
    assert r['multipliers'] == 9
    assert r['total'] == 14 * 9
    assert r['dupes'] == 1
    assert {reason for _, reason in r['excluded']} == {'duplicate', 'outside the contest period'}
    assert r['valid'][-1]['score'] == r['total']


def test_fixed_station_gets_no_activation_multipliers_and_a_warning():
    r = contests.score_vhf(log(JUNE_ROVER), ARRL_VHF_JUN, 'SO')
    assert r['multipliers'] == 7 and r['activated'] == []
    assert any('rule 6.3' in w for w in r['warnings'])


def test_category_band_and_mode_limits():
    df = log(JUNE_ROVER)
    so3b = contests.score_vhf(df, ARRL_VHF_JUN, 'SO3B')
    assert set(so3b['bands']) == {'50 MHz', '144 MHz'}
    sofm = contests.score_vhf(df, ARRL_VHF_JUN, 'SOFM')
    assert set(sofm['bands']) == {'222 MHz'}
    rl = contests.score_vhf(df, ARRL_VHF_JUN, 'RL')
    assert '10 GHz' not in rl['bands'] and '902 MHz' not in rl['bands']
    digital = log([('144', 'FT8', '2026-06-13', '1800', 'FN12', 'W2FU', 'FN13'),
                   ('144', 'CW', '2026-06-13', '1801', 'FN12', 'N2ZN', 'FN13')])
    assert contests.score_vhf(digital, ARRL_VHF_JUN, 'SO', analog_only=True)['qso_points'] == 1
    assert contests.score_vhf(digital, ARRL_VHF_JUN, 'SO')['qso_points'] == 2


def test_aeronautical_mobile_doesnt_count():
    df = log([('144', 'PH', '2026-06-13', '1800', 'FN12', 'W2FU/AM', 'FN13')])
    assert contests.score_vhf(df, ARRL_VHF_JUN, 'SO')['total'] == 0


def test_category_from_header():
    assert contests.category_from_header({'HQ-CATEGORY': 'Classic Rover'}) == 'R'
    assert contests.category_from_header({'CATEGORY-STATION': 'ROVER-LIMITED'}) == 'RL'
    assert contests.category_from_header({}, 'K2UA/R') == 'R'
    assert contests.category_from_header({'CATEGORY-OPERATOR': 'SINGLE-OP'}, 'K2UA') == 'SO'


ADIF = """Exported log <ADIF_VER:5>3.1.4 <EOH>
<CALL:4>W2FU <QSO_DATE:8>20260613 <TIME_ON:6>180000 <BAND:2>2m <MODE:3>SSB
<GRIDSQUARE:6>FN13ab <MY_GRIDSQUARE:4>FN12 <STATION_CALLSIGN:6>K2UA/R <CONTEST_ID:12>ARRL-VHF-JUN <EOR>
<call:4>N2ZN <qso_date:8>20260613 <time_on:4>1805 <freq:7>222.100 <mode:2>FM
<gridsquare:4>FN13 <station_callsign:6>K2UA/R <eor>
"""


def test_adif(tmp_path):
    path = tmp_path / 'rover.adi'
    path.write_text(ADIF)
    df, call = ds.resolve_source(str(path), verbose=False)
    assert call == 'K2UA/R'
    assert list(df['band']) == ['144 MHz', '222 MHz']
    assert list(df['sourcegrid']) == ['FN12', 'FN12']      # missing MY_GRIDSQUARE filled in
    assert list(df['grid']) == ['FN13AB', 'FN13']
    assert list(df['time']) == ['1800', '1805']
    assert list(df['date']) == ['2026-06-13', '2026-06-13']
    assert ds.read_log_header(str(path)) == {'CONTEST': 'ARRL-VHF-JUN'}


def test_vhf_cabrillo_script(tmp_path):
    rows = ["START-OF-LOG: 3.0", "CONTEST: ARRL-VHF-JUN", "CALLSIGN: K2UA/R",
            "HQ-CATEGORY: Classic Rover"]
    rows += [f"QSO: {b} {m} {d} {t} K2UA/R {mg} {c} {g}" for b, m, d, t, mg, c, g in JUNE_ROVER]
    rows.append("END-OF-LOG:")
    (tmp_path / 'rover.log').write_text('\n'.join(rows) + '\n')
    subprocess.run([sys.executable, f'{ROOT}/vhf_cabrillo.py', 'rover.log'],
                   cwd=tmp_path, check=True, capture_output=True, input='', text=True)
    summary = (tmp_path / 'K2UA-R_ARRL_VHF_JUN_Summary.txt').read_text()
    assert 'Score\t\t126' in summary and 'Classic Rover' in summary
    assert 'FN12' in summary and 'Rover stops' in summary
    cabrillo = (tmp_path / 'K2UA-R_ARRL_VHF_JUN.log').read_text()
    assert 'CONTEST: ARRL-VHF-JUN' in cabrillo and 'CLAIMED-SCORE: 126' in cabrillo
    assert 'CATEGORY-STATION: ROVER' in cabrillo
    assert cabrillo.count('\nQSO: ') == len(JUNE_ROVER)
    assert 'QSO: 222 FM 2026-06-14 0101 K2UA/R FN13 N2ZN FN13' in cabrillo
