import http.server
import socketserver
import urllib.parse
import re
import queue
import threading
import subprocess
import os
import sys
import time
from pathlib import Path

PORT = 3412

task_queue = queue.Queue()
state_lock = threading.Lock()
queued_tasks = set()          # store thread_id strings
currently_processing = set()  # store thread_id strings


def is_task_active(thread_id):
    with state_lock:
        return thread_id in queued_tasks or thread_id in currently_processing


def add_task(thread_id, limit_requests=None):
    with state_lock:
        print(task_queue, queued_tasks)
        if thread_id in queued_tasks or thread_id in currently_processing:
            return False
        task_queue.put((thread_id, limit_requests))
        queued_tasks.add(thread_id)
        print(f"Queued thread {thread_id} (limit: {limit_requests or 'unlimited'})")
        return True


def process_tasks():
    while True:
        thread_id, limit_requests = task_queue.get()

        with state_lock:
            queued_tasks.discard(thread_id)
            currently_processing.add(thread_id)

        print(f"Processing thread {thread_id}")
        try:
            tree_output = f"app/public/tree_{thread_id}.json"
            Path("app/public").mkdir(parents=True, exist_ok=True)

            cmd = ["python3", "load_thread_async.py"]
            if limit_requests:
                cmd.extend(["--limit-requests", str(limit_requests)])
            cmd.extend([thread_id, tree_output])
            print("Running:", cmd)

            proc = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            if proc.stdout: print(proc.stdout)
            if proc.stderr: print(proc.stderr, file=sys.stderr)

            print(f"Finished processing thread {thread_id}")
        except subprocess.CalledProcessError as e:
            print(f"Error processing thread {thread_id}: {e}", file=sys.stderr)
            if e.stdout: print("Stdout:", e.stdout, file=sys.stderr)
            if e.stderr: print("Stderr:", e.stderr, file=sys.stderr)
        except Exception as e:
            print(f"Unexpected error processing {thread_id}: {e}", file=sys.stderr)
        finally:
            with state_lock:
                currently_processing.discard(thread_id)
            task_queue.task_done()


class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if parsed.path == '/':
            if 'url' in qs:
                url = qs['url'][0]
                thread_id = None
                m = re.search(r'/status/(\d+)', url)
                if m:
                    thread_id = m.group(1)
                elif url.isdigit():
                    thread_id = url

                if not thread_id:
                    self.send_error(400, "Invalid URL: could not extract thread ID")
                    return

                tree_file = f"app/public/tree_{thread_id}.json"
                limit_requests = qs.get('limit_requests', [None])[0]

                redirect_url = f"http://localhost:5000/#{thread_id}"

                # If ready and fresh, redirect to target
                if os.path.exists(tree_file) and (time.time() - os.path.getmtime(tree_file) < 60):
                    self.send_response(302)
                    self.send_header('Location', redirect_url)
                    self.end_headers()
                    return

                add_task(thread_id, int(limit_requests) if limit_requests else None)

                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()

                refresh_target = self.path  # keep the same query so we retry same request
                html = f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="color-scheme" content="light dark">
    <title>Loading thread {thread_id}...</title>
  </head>
  <body>
    <span>Loading thread {thread_id}...</span>
    <script>
      function checkStatus() {{
        document.querySelector('span').textContent += ' .';
        fetch("{refresh_target}", {{ redirect: 'manual' }})
          .then(response => {{
            if (response.type === 'opaqueredirect') {{
              window.location.href =  {redirect_url!r};
            }} else {{
              setTimeout(checkStatus, 1000);
            }}
          }})
          .catch(() => {{
            setTimeout(checkStatus, 1000);
          }});
      }}
      checkStatus();
    </script>
  </body>
</html>"""
                self.wfile.write(html.encode('utf-8'))
            else:
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(b"""<!DOCTYPE html>
<html>
  <head><meta charset="utf-8"><title>Submit</title><meta name="color-scheme" content="light dark"></head>
  <body>
    <h1>Submit a thread URL or ID</h1>
    <form action="/" method="get">
      <input type="text" name="url" size="100">
      <input type="submit" value="Load">
    </form>
  </body>
</html>""")
        else:
            self.send_error(404, "Not Found")


def main():
    worker = threading.Thread(target=process_tasks, daemon=True)
    worker.start()

    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        httpd.allow_reuse_address = True
        print(f"Serving at http://localhost:{PORT}")
        httpd.serve_forever()


if __name__ == '__main__':
    main()
