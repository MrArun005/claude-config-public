"""P0 exit-criterion runner. Run on YOUR machine after triggering a code.

  python p0_test.py proxify

Exit criterion (plan §6 P0): three consecutive retrievals, zero keystrokes,
median latency < 10s. Run it three times; it appends to p0_results.txt.
"""
import asyncio, sys, time
from identity.otp import GmailMailbox, wait_for_otp

async def main():
    hint = sys.argv[1] if len(sys.argv) > 1 else "proxify"
    t0 = time.time() - 300
    start = time.time()
    code = await wait_for_otp(GmailMailbox(), hint, since_ts=t0, timeout=120)
    latency = time.time() - start
    line = f"{time.strftime('%H:%M:%S')}  {hint}  code={code}  latency={latency:.1f}s"
    print(line)
    with open("p0_results.txt", "a") as fh:
        fh.write(line + "\n")

asyncio.run(main())
