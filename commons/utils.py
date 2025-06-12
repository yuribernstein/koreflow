import time
import functools

def retry_this(timeout, interval=0.1, exceptions=(Exception,), verbose=False):
    """
    Retry a function until it succeeds or timeout is reached.

    Args:
        timeout (float): total timeout in seconds.
        interval (float): sleep time between retries.
        exceptions (tuple): which exceptions to catch and retry.
        verbose (bool): log retry attempts (default: False).
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            end_time = time.time() + timeout
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if time.time() >= end_time:
                        raise
                    if verbose:
                        print(f"[retry_this] Exception: {e} — retrying...")
                    time.sleep(interval)
        return wrapper
    return decorator
