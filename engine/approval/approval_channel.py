# approval_channel.py

import queue

# From WE to Flask: (register|deregister, payload)
approval_request_q = queue.Queue()

# From Flask to WE: (uid, step_id, status) — status: 'approved' | 'timeout'
approval_result_q = queue.Queue()
