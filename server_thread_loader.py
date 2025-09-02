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
queued_tasks = set()
currently_processing = set()


def is_task_active(thread_id):
    with state_lock:
        return thread_id in queued_tasks or thread_id in currently_processing


def add_task(thread_id):
    with state_lock:
        if thread_id in queued_tasks or thread_id in currently_processing:
            return False  # not added
        task_queue.put(thread_id)
        queued_tasks.add(thread_id)
        print(f"Queued thread {thread_id}")
        return True  # added


def process_tasks():
    while True:
        thread_id = task_queue.get()

        with state_lock:
            queued_tasks.remove(thread_id)
            currently_processing.add(thread_id)
        
        print(f"Processing thread {thread_id}")

        try:
            raw_output = f"threads/thread_{thread_id}.json"
            tree_output = f"app/public/tree_{thread_id}.json"

            Path("threads").mkdir(exist_ok=True)
            Path("app/public").mkdir(exist_ok=True)

            print(f"Running load_thread_async.py for {thread_id}")
            proc = subprocess.run(
                ["python3", "load_thread_async.py", thread_id, raw_output],
                check=True,
                capture_output=True, text=True,
                encoding='utf-8'
            )
            if proc.stdout: print(proc.stdout)
            if proc.stderr: print(proc.stderr, file=sys.stderr)

            print(f"Running thread_to_tree_grouped.py for {thread_id}")
            proc = subprocess.run(
                ["python3", "thread_to_tree_grouped.py", raw_output, tree_output],
                check=True,
                capture_output=True, text=True,
                encoding='utf-8'
            )
            if proc.stdout: print(proc.stdout)
            if proc.stderr: print(proc.stderr, file=sys.stderr)

            print(f"Finished processing thread {thread_id}")
        except subprocess.CalledProcessError as e:
            print(f"Error processing thread {thread_id}", file=sys.stderr)
            if e.stdout: print("Stdout:", e.stdout, file=sys.stderr)
            if e.stderr: print("Stderr:", e.stderr, file=sys.stderr)
        except Exception as e:
            print(f"An unexpected error occurred while processing {thread_id}: {e}", file=sys.stderr)
        finally:
            with state_lock:
                currently_processing.remove(thread_id)
            task_queue.task_done()


class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)

        if parsed_path.path == '/':
            if 'url' in query_params:
                url = query_params['url'][0]
                thread_id = None
                match = re.search(r'/status/(\d+)', url)
                if match:
                    thread_id = match.group(1)
                elif url.isdigit():
                    thread_id = url
                
                if thread_id:
                    tree_file = f"app/public/tree_{thread_id}.json"
                    if not os.path.exists(tree_file) or (time.time() - os.path.getmtime(tree_file) > 60):
                        add_task(thread_id)
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(f"""
                    <!DOCTYPE html>
                    <html>
                        <head>
                            <meta name="color-scheme" content="light dark">
                            <title>Loading thread...</title>
                            <meta charset="utf-8">
                            <script>
                                const thread_id = '{thread_id}';
                                function checkStatus() {{
                                    fetch('/check?thread_id=' + thread_id)
                                        .then(response => response.json())
                                        .then(data => {{
                                            if (data.status === 'done') {{
                                                document.getElementById('status').textContent = 'Done! Redirecting...';
                                                window.location.href = `http://localhost:5000/#${{thread_id}}`;
                                            }} else {{
                                                setTimeout(checkStatus, 2000);
                                            }}
                                        }})
                                        .catch(() => setTimeout(checkStatus, 2000));
                                }}
                                document.addEventListener('DOMContentLoaded', checkStatus);
                            </script>
                        </head>
                        <body>
                            <h1 id="status">Loading thread {thread_id}...</h1>
                            <p>You will be redirected automatically when it's ready.</p>
                        </body>
                    </html>
                    """.encode('utf-8'))
                else:
                    self.send_error(400, "Invalid URL: could not extract thread ID")
            else:
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(b"""
                <!DOCTYPE html>
                <html>
                    <head>
                        <meta name="color-scheme" content="light dark">
                    </head>
                    <body>
                        <h1>Submit a thread URL or ID</h1>
                        <form action="/" method="get">
                            <input type="text" name="url" size="100">
                            <input type="submit" value="Load">
                        </form>
                    </body>
                </html>
                """)

        elif parsed_path.path == '/check':
            if 'thread_id' in query_params:
                thread_id = query_params['thread_id'][0]
                tree_output = f"app/public/tree_{thread_id}.json"

                if os.path.exists(tree_output) and time.time() - os.path.getmtime(tree_output) < 60:
                    status = "done"
                else:
                    status = "pending"
                    if not is_task_active(thread_id):
                        if add_task(thread_id):
                            print(f"Re-queued thread {thread_id} from check")

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(f'{{"status": "{status}"}}'.encode('utf-8'))
            else:
                self.send_error(400, "Missing thread_id")
        else:
            self.send_error(404, "Not Found")


def main():
    worker = threading.Thread(target=process_tasks, daemon=True)
    worker.start()

    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        httpd.serve_forever()


if __name__ == '__main__':
    main()
