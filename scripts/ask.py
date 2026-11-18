#!/usr/bin/env python3
"""Ask the offline snapshot knowledge system."""
import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'harness'))
from run_eval import load_snapshots, load_submission

def main():
    p=argparse.ArgumentParser()
    p.add_argument('question')
    p.add_argument('--as-of')
    p.add_argument('--snapshots',type=Path,default=ROOT/'snapshots')
    args=p.parse_args()
    ks=load_submission(ROOT/'submission')
    for s in load_snapshots(args.snapshots):ks.ingest(s)
    print(json.dumps(asdict(ks.answer(args.question,args.as_of)),indent=2,ensure_ascii=False))
if __name__=='__main__':main()
