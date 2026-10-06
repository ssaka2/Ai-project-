"""Private pilot acceptance checks. No application submissions or database writes."""
import argparse
import json
from datetime import datetime, timezone
from urllib.request import Request, build_opener, ProxyHandler
import ai_staff
import recruiting


def read_office(port, path, data=None, token=None):
    headers={'Accept':'application/json'}
    raw=None
    if data is not None:
        raw=json.dumps(data).encode()
        headers.update({'Content-Type':'application/json','X-Office-Token':token or ''})
    request=Request(f'http://127.0.0.1:{port}'+path,data=raw,headers=headers)
    with build_opener(ProxyHandler({}),ai_staff.NoRedirect()).open(request,timeout=8) as response:
        body=response.read(5_000_001)
    if len(body)>5_000_000:raise ValueError('Office response too large')
    return json.loads(body)


def verify(port, boards, test_model=False):
    checks=[]
    model=None
    try:
        # The local API returns the workspace alongside its token. Never log or
        # include that payload, its profiles, or its token in the report.
        state=read_office(port,'/api/state')
        token=state['token']
        del state
        readiness=read_office(port,'/api/readiness',{},token)
        model=readiness.get('model')
        checks.append(dict(check='office_http',status='pass'))
        checks.append(dict(check='model_inventory',status='pass' if readiness['status']=='model_available' else 'blocked',detail=readiness['status']))
    except Exception as exc:
        checks.append(dict(check='office_http',status='blocked',detail=type(exc).__name__))
    if test_model and model:
        try:
            # Fixed fictional data only. Does not use task context or candidate CVs.
            result=ai_staff.generate(model,'Synthetic acceptance test. Fictional candidate Test Person has Python skills and one fictional test project. Draft a short factual profile and list missing job requirements. No applications exist. Never claim a submission. This output is for a test only.')
            checks.append(dict(check='synthetic_model_generation',status='pass',output_characters=len(result),detail='Transport and nonempty response verified; factual quality requires separate review.'))
        except Exception as exc:
            checks.append(dict(check='synthetic_model_generation',status='blocked',detail=type(exc).__name__))
    else:
        checks.append(dict(check='synthetic_model_generation',status='not_tested',detail='Requires --test-model and a configured model on the running office.'))
    for board in boards:
        try:
            jobs=recruiting.fetch_board(board)
            checks.append(dict(check='live_source',source=board,status='pass',postings=len(jobs),detail='Read access only; publication freshness and candidate eligibility not verified.'))
        except Exception as exc:
            checks.append(dict(check='live_source',source=board,status='blocked',detail=type(exc).__name__))
    if not boards:checks.append(dict(check='live_source',status='not_tested',detail='Specify at least one real employer board with --board.'))
    passed=all(c['status']=='pass' for c in checks)
    return dict(checked_at=datetime.now(timezone.utc).isoformat(),pilot_connectivity_verified=passed,
                production_staffing_ready=False,checks=checks,
                remaining=['AI document quality evaluation','Authorized submission integration','Inbox/status integration','Candidate accounts and access isolation','Backup and recovery validation'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=4521)
    parser.add_argument('--board',action='append',default=[],help='Real Greenhouse token or lever:company; repeat up to five times')
    parser.add_argument('--test-model',action='store_true',help='Run one local inference with fixed fictional input; may consume local compute')
    args=parser.parse_args()
    if not 1<=args.port<=65535 or len(args.board)>5:parser.error('Valid port and at most five boards required')
    try:boards=list(dict.fromkeys(recruiting.normalize_board(b) for b in args.board))
    except ValueError as exc:parser.error(str(exc))
    report=verify(args.port,boards,args.test_model)
    print(json.dumps(report,indent=2))
    return 0 if report['pilot_connectivity_verified'] else 2

if __name__=='__main__':raise SystemExit(main())
