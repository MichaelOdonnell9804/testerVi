import sys
import json
import ROOT
from pathlib import Path

# Append the local ``exp`` directory to ``sys.path`` so that bundled
# modules such as ``CMSPLOTS`` are imported from this repository even if
# other versions are installed in the environment.  Insert at the front
# only if it has not been added already.
exp_path = str(Path(__file__).resolve().parent / 'exp')
if exp_path not in sys.path:
    sys.path.insert(0, exp_path)

from utils.channel_map import build_map_FERS1_ixy
from CMSPLOTS.myFunction import DrawHistos

ROOT.gROOT.SetBatch(True)


def build_horizontal_map():
    base = build_map_FERS1_ixy()
    maps = {}
    for board in range(1, 6):
        shift = 4 * (board - 1)
        bmap = {ch: (ix + shift, iy) for ch, (ix, iy) in base.items()}
        maps[f"Board{board}"] = bmap
    return maps


def display_event(root_file, event_number):
    noise_file = Path(__file__).resolve().parent / 'exp' / 'results' / 'fers_noises.json'
    with open(noise_file, 'r') as f:
        noises = json.load(f)

    infile = ROOT.TFile(root_file, 'READ')
    if not infile or infile.IsZombie():
        raise RuntimeError(f'Failed to open {root_file}')

    rdf = ROOT.RDataFrame('EventTree', infile)
    rdf_evt = rdf.Filter(f'event_n == {int(event_number)}')
    if rdf_evt.Count().GetValue() == 0:
        raise RuntimeError(f'Event {event_number} not found in file')

    maps = build_horizontal_map()
    hist = ROOT.TH2F('event', f'Event {event_number};X;Y', 20, -0.5, 19.5, 8, -0.5, 7.5)

    # Determine whether the per-channel columns already exist or if the
    # energies are stored in array branches.  ``GetColumnNames`` returns a
    # ``std::vector<string>`` which supports Python's ``in`` operator.
    columns = set(str(c) for c in rdf.GetColumnNames())

    for board in range(1, 6):
        array_col = f'FERS_Board{board}_energyHG'

        # Cache the vector of energies if the data is stored as an array
        energies = None
        if array_col in columns:
            energies = rdf_evt.Take['ROOT::VecOps::RVec<unsigned short>'](
                array_col).GetValue()[0]

        for ch in range(64):
            col_split = f'{array_col}_{ch}'

            if col_split in columns:
                val = rdf_evt.Take['unsigned short'](col_split).GetValue()[0]
            elif energies is not None:
                val = int(energies[ch])
            else:
                raise RuntimeError(f'Column {col_split} not found')
            ix, iy = maps[f'Board{board}'][ch]
            noise_key = f'board{board}_ch{ch}'
            val_adj = val - noises.get(noise_key, 0)
            hist.Fill(ix, iy, val_adj)

    DrawHistos([hist], '', -0.5, 19.5, 'iX', -0.5, 7.5, 'iY',
               f'event_display_{event_number}', dology=False,
               drawoptions=['COLZ,text'], doth2=True, zmin=0, zmax=8000,
               W_ref=1400)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python plotter.py <file.root> <eventNumber>')
        sys.exit(1)
    display_event(sys.argv[1], sys.argv[2])
