"""Exercise an image upload in WebView2 using the app's actual content policy.

Usage: python tools/verify_portrait_decode.py path/to/image.png
Runs hidden windows; does not open or modify any user story.
"""
import base64
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import threading
import webview


class PolicyParser(HTMLParser):
    policy = ''
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and attrs.get('http-equiv') == 'Content-Security-Policy':
            self.policy = attrs['content']


def main():
    parser = PolicyParser()
    parser.feed((Path(__file__).resolve().parents[1]/'preview/index.html').read_text())
    raw = base64.b64encode(Path(sys.argv[1]).read_bytes()).decode()
    results = {}
    windows = []
    script = '''(async () => {
      const bytes = Uint8Array.from(atob(INPUT), c => c.charCodeAt(0));
      const url = URL.createObjectURL(new Blob([bytes], {type:'image/png'}));
      try {
        const photo = new Image(); photo.src = url; await photo.decode();
        const scale = Math.min(1,768 / Math.max(photo.naturalWidth, photo.naturalHeight));
        const canvas = document.createElement('canvas');
        canvas.width = Math.round(photo.naturalWidth*scale);
        canvas.height = Math.round(photo.naturalHeight*scale);
        canvas.getContext('2d').drawImage(photo,0,0,canvas.width,canvas.height);
        const jpeg=canvas.toDataURL('image/jpeg',0.88);
        return {decoded:true,width:photo.naturalWidth,height:photo.naturalHeight,
          outputWidth:canvas.width,outputHeight:canvas.height,jpeg:jpeg.startsWith('data:image/jpeg;base64,')};
      } catch(e) { return {decoded:false,error:e.message}; }
      finally { URL.revokeObjectURL(url); }
    })()'''.replace('INPUT',json.dumps(raw))
    def close_all():
        for window in windows:
            window.destroy()
    def loaded(window, name):
        def complete(result):
            results[name]=result
            if len(results)==2:close_all()
        window.evaluate_js(script,complete)
    for name, policy in [('before',parser.policy.replace("img-src 'self' data: blob:; ",'')),('fixed',parser.policy)]:
        html=f'<html><head><meta http-equiv="Content-Security-Policy" content="{policy}"></head><body>Portrait decode test</body></html>'
        window=webview.create_window('Portrait regression test',html=html,hidden=True)
        window.events.loaded += lambda w=window,n=name: loaded(w,n)
        windows.append(window)
    timer=threading.Timer(30,close_all)
    timer.start()
    try:webview.start(gui='edgechromium',private_mode=True)
    finally:timer.cancel()
    print(json.dumps(results,indent=2))
    assert results['before']['decoded'] is False, 'Original policy should reproduce the failure'
    assert results['fixed']['decoded'] and results['fixed']['jpeg'], 'Corrected policy must decode and convert'


if __name__=='__main__':main()
