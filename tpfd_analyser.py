import re
import json
import csv
import os
import sys
from collections import defaultdict

# ======================= CONFIGURATION =======================
INPUT_DIR = '/Users/XXXX/Downloads/chopper_tune/adxl_results/chopper_magnitude'   # folder with tpfd html-files
CSV_OUTPUT = 'tpfd_analysis.csv'           # Export CSV to same folder
# ============================================================

def extract_data(html_content):
    """
    Extract the data array from the HTML content.
    Looks for a JSON array starting with '[{' and containing traces with 'x' and 'y'.
    Returns the parsed list of traces, or None if not found.
    """
    start = 0
    while True:
        start = html_content.find('[{"', start)
        if start == -1:
            return None
        bracket_count = 0
        end = None
        for i in range(start, len(html_content)):
            ch = html_content[i]
            if ch == '[':
                bracket_count += 1
            elif ch == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    end = i + 1
                    break
        if end is None:
            start += 1
            continue
        candidate = html_content[start:end]
        try:
            data = json.loads(candidate)
            if (isinstance(data, list) and len(data) > 0 and
                isinstance(data[0], dict) and 'x' in data[0] and 'y' in data[0]):
                if any('freq=' in str(item.get('y', '')) for item in data):
                    return data
        except json.JSONDecodeError:
            pass
        start += 1
    return None

def parse_trace(trace):
    """
    Parse a single trace (dict) and extract amplitude, label, frequency, and tpfd.
    Returns a tuple (amplitude, label, frequency, tpfd) or None if parsing fails.
    """
    if 'y' not in trace or not trace['y'] or 'x' not in trace or not trace['x']:
        return None
    label = trace['y'][0]
    amp = trace['x'][0]
    # Extract frequency
    freq_match = re.search(r'freq=([\d.]+)kHz', label)
    if not freq_match:
        return None
    freq = float(freq_match.group(1))
    # Extract tpfd (can be negative)
    tpfd_match = re.search(r'tpfd=([-+]?\d+)', label)
    if not tpfd_match:
        tpfd = None
    else:
        tpfd = int(tpfd_match.group(1))
    return (amp, label, freq, tpfd)

def process_file(filepath):
    """
    Process a single HTML file: extract data, parse each trace, return list of results.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            html = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []
    data = extract_data(html)
    if data is None:
        print(f"No valid data found in {filepath}")
        return []
    results = []
    for trace in data:
        parsed = parse_trace(trace)
        if parsed:
            results.append(parsed)
    return results

def main():
    # 1. Find all HTML files in INPUT_DIR
    if not os.path.isdir(INPUT_DIR):
        print(f"Directory not found: {INPUT_DIR}")
        sys.exit(1)
    html_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.html')]
    if not html_files:
        print(f"No HTML files found in {INPUT_DIR}")
        sys.exit(1)
    print(f"Found {len(html_files)} HTML file(s) in {INPUT_DIR}")

    # 2. Process each file and collect all traces
    all_results = []
    for filename in html_files:
        filepath = os.path.join(INPUT_DIR, filename)
        print(f"Processing: {filename}")
        results = process_file(filepath)
        if results:
            all_results.extend(results)
            print(f"  -> Extracted {len(results)} traces")
        else:
            print(f"  -> No valid traces")

    if not all_results:
        print("No valid traces found in any file.")
        sys.exit(1)

    print(f"\nTotal traces extracted: {len(all_results)}")

    # 3. Sort by amplitude (ascending)
    all_results.sort(key=lambda x: x[0])  # sort by amplitude

    # 4. Print table to console
    print("\n=== Sorted by Amplitude (lowest first) ===")
    print(f"{'Rank':>4} | {'Amplitude':>10} | {'Freq (kHz)':>10} | {'tpfd':>6} | Parameter")
    print("-" * 80)
    for idx, (amp, label, freq, tpfd) in enumerate(all_results, start=1):
        tpfd_str = str(tpfd) if tpfd is not None else "N/A"
        print(f"{idx:4} | {amp:10.2f} | {freq:10.2f} | {tpfd_str:>6} | {label}")

    # 5. Statistics (optional)
    amps = [r[0] for r in all_results]
    print(f"\nStatistics:")
    print(f"  Min amplitude: {min(amps):.2f}")
    print(f"  Max amplitude: {max(amps):.2f}")
    print(f"  Mean amplitude: {sum(amps)/len(amps):.2f}")

    # 6. Export to CSV (in the same directory as INPUT_DIR)
    csv_path = os.path.join(INPUT_DIR, CSV_OUTPUT)
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Rank', 'Amplitude', 'Frequency_kHz', 'tpfd', 'Parameter'])
        for idx, (amp, label, freq, tpfd) in enumerate(all_results, start=1):
            writer.writerow([idx, amp, freq, tpfd, label])
    print(f"\nAll data saved to: {csv_path}")

if __name__ == '__main__':
    main()