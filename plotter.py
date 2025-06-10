import sys
import json
import ROOT
from pathlib import Path

# Append exp directories for local modules
exp_path = Path(__file__).resolve().parent / 'exp'
sys.path.append(str(exp_path))
sys.path.append(str(exp_path / 'CMSPLOTS'))

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

    for board in range(1, 6):
        for ch in range(64):
            val = rdf_evt.Take['unsigned short'](f'FERS_Board{board}_energyHG_{ch}').GetValue()[0]
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
