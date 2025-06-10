import sys
import json
import ROOT
from pathlib import Path
from utils.channel_map import build_map_FERS1_ixy

# ensure we import your local CMSPLOTS package first
exp_pkg = Path(__file__).resolve().parent / 'exp' / 'CMSPLOTS'
sys.path.insert(0, str(exp_pkg))
from CMSPLOTS.myFunction import DrawHistos

def build_horizontal_map():
    """
    Take boards [4,3,2,1,0], tile them across x=0..19 in 4-column blocks
    (wrap at 20), and drop only Board 2 down by 4 rows.
    """
    base = build_map_FERS1_ixy()   # per-board geometry for 64 channels
    maps = {}
    board_order = [4, 3, 2, 1, 0]
    for idx, board in enumerate(board_order):
        # horizontal shift: 4,8,12,16,0
        shift_x = (4 * (idx + 1)) % 20
        # vertical shift only for the “middle” board (Board 2)
        shift_y = -4 if board == 3 else 0

        maps[f"Board{board}"] = {
            ch: ((ix + shift_x) % 20, iy + shift_y)
            for ch, (ix, iy) in base.items()
        }
    return maps

def display_event(root_file, event_number):
    # 1) load noise map
    noise_path = Path(__file__).parent / 'exp' / 'results' / 'fers_noises.json'
    noises = json.load(open(noise_path))

    # 2) open file & grab tree
    infile = ROOT.TFile(root_file, 'READ')
    if infile.IsZombie():
        raise RuntimeError(f"Failed to open {root_file}")
    tree = infile.Get("EventTree")
    if not tree:
        raise RuntimeError("EventTree not found in file")

    # 3) find the entry matching event_n
    evt = int(event_number)
    entry_id = None
    for i in range(tree.GetEntries()):
        tree.GetEntry(i)
        if tree.event_n == evt:
            entry_id = i
            break
    if entry_id is None:
        raise RuntimeError(f"Event {evt} not found")
    tree.GetEntry(entry_id)

    # 4) build map & 20×12 histogram (x=0..19, y=-4..7)
    maps = build_horizontal_map()
    hist = ROOT.TH2F(
        'event', f'Event {evt};iX;iY',
        20, -0.5, 19.5,   # x bins 0..19
        12, -4.5,  7.5    # y bins -4..7
    )

    # 5) fill from the C-array branches
    for board in [4, 3, 2, 1, 0]:
        arr = getattr(tree, f"FERS_Board{board}_energyHG")
        for ch, raw in enumerate(arr):
            ix, iy = maps[f"Board{board}"][ch]
            hist.Fill(ix, iy, int(raw))

    # 6) draw with full palette + labels, no CMS/lumi
    zmax = hist.GetMaximum()
    DrawHistos(
        [hist], '', -0.5, 19.5, 'iX', -4.5, 7.5, 'iY',
        f'event_display_{evt}',
        dology=False,
        drawoptions=['COLZ0 TEXT0'],
        doth2=True,
        zmin=0, zmax=zmax,
        W_ref=1400,
        noLumi=True,
        noCMS=True
    )

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python plotter.py <file.root> <eventNumber>')
        sys.exit(1)
    display_event(sys.argv[1], sys.argv[2])
