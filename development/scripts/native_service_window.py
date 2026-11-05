#!/usr/bin/env python3
"""Decode the explicit physical five-second post-method service observation."""
import struct

MODES = {1: 'first-method', 2: 'first-display-client-attempt',
         3: 'first-display-client', 4: 'first-method-plus-5s', 5: 'observer-bound'}
MAGIC = 0x315753485052

def checkpoint_mode(marker, read, symbols):
    assert marker in MODES, 'Unknown watchdog checkpoint marker'
    if marker == 4:
        assert '_raphael_native_service_window_record' in symbols
        assert struct.unpack('<I', read(symbols['_raphael_native_service_window_seconds'], 4))[0] == 5, 'Only the explicit five-second service window is qualified'
    return MODES[marker]

def decode_service_window(read, symbols, watchdog, capture_counter):
    words = struct.unpack('<8Q', read(symbols['_raphael_native_service_window_record'], 64))
    if not any(words):
        return dict(started=False, completed=False, requested_ms=5000)
    magic, version, frequency, start, end, ticks, calls, checkins = words
    assert magic == MAGIC and version == 1
    assert 0 < frequency <= 1000000000 and ticks == frequency * 5
    assert 0 < start <= capture_counter and calls > 0
    if watchdog:
        assert frequency == watchdog['counter_frequency'], 'Service window counter frequency differs from watchdog'
        assert watchdog['start_counter'] <= start <= watchdog['stop_counter'] <= capture_counter
    if end:
        assert start <= end <= capture_counter and end - start >= ticks, 'Service window ended before five physical seconds'
        if watchdog:
            assert end <= watchdog['stop_counter']
            assert end < watchdog['start_counter'] + watchdog['deadline_ticks']
            assert end <= watchdog['start_counter'] + watchdog['observer_deadline_ticks']
    return dict(started=True, completed=bool(end), requested_ms=5000,
                counter_frequency=frequency, start_counter=start, end_counter=end,
                elapsed_ms=(end-start)*1000/frequency if end else None,
                method_calls_at_start=calls, checkins_at_start=checkins)
