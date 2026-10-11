"""Browser check with synthetic facts and an injected model; not live inference."""
import threading
import re
import unittest
from unittest.mock import patch
from contextlib import closing
from playwright.sync_api import sync_playwright, expect
import office
import worker_runtime
import worker_store
from worker_test_support import fixture


def main():
    owner=unittest.TestCase()
    app,candidate,tasks=fixture(owner)
    server=office.make_server(app.path,0)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch();page=browser.new_page(viewport={'width':1280,'height':900})
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{server.server_port}')
            expect(page.locator('#connection-title')).to_have_text('Backend connected')
            expect(page.locator('#worker-candidate')).to_be_visible()
            page.locator('#worker-candidate').select_option(str(candidate))
            page.locator('#worker-portfolio').fill('Verified synthetic project <img src=x onerror=alert(1)> https://example.com/demo')
            page.locator('#worker-enabled').check()
            page.get_by_role('button',name='Save automation settings',exact=True).click()
            expect(page.locator('#worker-message')).to_contain_text('saved')
            worker_runtime.enqueue_eligible(app,now=100)
            worker_runtime.run_once(app,now_fn=lambda:100,provider=lambda m,p:'Synthetic draft <img src=x onerror=alert(1)>')
            page.get_by_role('button',name='Refresh worker status',exact=True).click()
            expect(page.locator('#worker-runs')).to_contain_text('succeeded',timeout=10000)
            page.locator('#worker-candidate').select_option('')
            page.locator('#workflow-candidate').select_option(str(candidate))
            expect(page.locator('#workflow-floor')).to_contain_text('succeeded')
            page.locator('#worker-candidate').select_option(str(candidate))
            # Current workflow execution must refresh even on an older history page.
            for i in range(30):
                worker_store.enqueue(app,task_id=tasks[4]['id'],task_version=2,candidate_id=candidate,executor='portfolio_draft',fingerprint=f'history-{i}',now=100)
            with closing(app.connect()) as db,db:
                db.execute("UPDATE worker_runs SET state='failed' WHERE state='queued'")
            current=worker_store.enqueue(app,task_id=tasks[3]['id'],task_version=2,candidate_id=candidate,executor='cv_draft',fingerprint='status-fixture',now=100)
            current=worker_store.claim(app,now=100)
            page.get_by_role('button',name='Refresh worker status',exact=True).click()
            expect(page.locator('#workflow-floor')).to_contain_text('1 running',timeout=10000)
            page.get_by_role('button',name='Older worker runs',exact=True).click()
            expect(page.locator('#worker-runs')).not_to_contain_text(f"Run #{current['id']} ·")
            draft_id=app.snapshot()['ai_drafts'][0]['id']
            worker_store.finish(app,current['id'],current['lease_token'],state='succeeded',now=101,result_ref=draft_id)
            expect(page.locator('#workflow-floor')).to_contain_text('1 succeeded',timeout=12000)
            expect(page.locator('#workflow-floor')).not_to_contain_text('1 running')
            page.locator('#workflow-candidate').select_option('')
            expect(page.locator('#workflow-floor')).not_to_contain_text('Workers:')
            page.locator('#workflow-candidate').select_option(str(candidate))
            expect(page.locator('#workflow-floor')).to_contain_text('1 succeeded',timeout=10000)
            page.locator('#worker-portfolio').fill('Unsaved project inventory')
            page.get_by_role('button',name='Refresh worker status',exact=True).click()
            expect(page.locator('#worker-portfolio')).to_have_value('Unsaved project inventory')
            page.reload()
            page.locator('#worker-candidate').select_option(str(candidate))
            expect(page.locator('#worker-runs')).to_contain_text('succeeded',timeout=10000)
            expect(page.locator('#worker-capabilities')).to_contain_text('No authorized submission adapter')
            page.get_by_role('button',name='Refresh',exact=True).click()
            expect(page.locator('#board').get_by_label('Unverified AI draft')).to_have_value(re.compile(r'Synthetic draft <img src=x onerror=alert\(1\)>'))
            assert page.locator('#board img').count()==0
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            page.screenshot(path='/tmp/ai-office-workers-mobile.png',full_page=True)
            assert not errors,errors
            browser.close()
    finally:
        server.shutdown();server.server_close();thread.join(2);owner.doCleanups()
    print('Worker Chromium: settings, synthetic execution, history, 3D, unsaved input, text safety and mobile passed.')

if __name__=='__main__':main()
