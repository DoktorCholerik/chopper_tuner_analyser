import re
import json
import csv
import sys
import os
from collections import defaultdict

# ======================= CONFIGURATION =======================
FREQ_MIN = 20          # kHz (lower bound recommended by TMC)
FREQ_MAX = 50          # kHz (upper bound recommended by TMC)
HTML_FILE = '/Users/XXXXX/Downloads/chopper_tune/sorted_interactive_plot_lis2dw_tmc5160_0.075_XXXXXXXXXX.html'
# Insert here your path to your "sorted_interactive_plot_XXX.html"
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

def parse_traces(data):
    """
    Parse frequency, amplitude, and the full label string from each trace.
    Expects the label to contain 'freq=...kHz'.
    Returns a list of tuples (frequency, amplitude, label).
    """
    results = []
    for trace in data:
        if 'y' in trace and trace['y'] and 'x' in trace and trace['x']:
            label = trace['y'][0]
            amp = trace['x'][0]
            freq_match = re.search(r'freq=([\d.]+)kHz', label)
            if freq_match:
                freq = float(freq_match.group(1))
                results.append((freq, amp, label))
    return results

def filter_by_frequency(results, f_min, f_max):
    """Filter results to the frequency range [f_min, f_max] (inclusive)."""
    return [(f, a, l) for f, a, l in results if f_min <= f <= f_max]

def group_by_frequency(entries):
    """
    Group entries by frequency (rounded to 2 decimals).
    For each group, keep only the entry with the minimum amplitude.
    Returns a sorted list of tuples:
        (frequency, min_amplitude, parameter_string)
    """
    grouped = defaultdict(list)
    for f, a, l in entries:
        key = round(f, 2)          # round frequency to 2 decimals
        grouped[key].append((f, a, l))
    
    best_per_freq = []
    for freq_key, items in grouped.items():
        # Pick the entry with the smallest amplitude
        best = min(items, key=lambda x: x[1])
        best_per_freq.append((freq_key, best[1], best[2]))
    # Sort by frequency
    best_per_freq.sort(key=lambda x: x[0])
    return best_per_freq

def export_csv(data, filename):
    """Write the grouped data to a CSV file."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Frequency_kHz', 'Min_Amplitude', 'Parameter'])
        for freq, amp, label in data:
            writer.writerow([freq, amp, label])

def print_statistics(data):
    """Print statistical summary for the grouped data."""
    if not data:
        print("No data available for statistics.")
        return
    amps = [a for _, a, _ in data]
    freqs = [f for f, _, _ in data]
    print(f"  Number of distinct frequencies: {len(data)}")
    print(f"  Amplitude - Min: {min(amps):.2f}, Max: {max(amps):.2f}, Mean: {sum(amps)/len(amps):.2f}")
    print(f"  Frequency - Min: {min(freqs):.2f}, Max: {max(freqs):.2f}")

def main():
    # 1. Read HTML file
    try:
        with open(HTML_FILE, 'r', encoding='utf-8') as f:
            html = f.read()
    except FileNotFoundError:
        print(f"File not found: {HTML_FILE}")
        sys.exit(1)

    # 2. Extract data array
    data = extract_data(html)
    if data is None:
        print("No valid data array found.")
        sys.exit(1)
    print(f"Loaded {len(data)} traces.")

    # 3. Parse frequencies and amplitudes
    results = parse_traces(data)
    if not results:
        print("No frequency information found in the labels.")
        sys.exit(1)
    print(f"Extracted {len(results)} valid data points.")

    # 4. Filter by the desired frequency range
    filtered = filter_by_frequency(results, FREQ_MIN, FREQ_MAX)
    if not filtered:
        print(f"\nNo entries found in the frequency range {FREQ_MIN}–{FREQ_MAX} kHz.")
        # Fallback: show the nearest available frequencies
        max_freq = max(results, key=lambda x: x[0])
        min_freq = min(results, key=lambda x: x[0])
        print(f"\nHighest frequency in dataset: {max_freq[0]:.2f} kHz")
        print(f"   Corresponding amplitude: {max_freq[1]:.2f}")
        print(f"   Parameter: {max_freq[2]}")
        print(f"\nLowest frequency in dataset: {min_freq[0]:.2f} kHz")
        print(f"   Corresponding amplitude: {min_freq[1]:.2f}")
        print(f"   Parameter: {min_freq[2]}")
        sys.exit(0)

    # 5. Group by frequency and keep the best (min amplitude) per frequency
    best_per_freq = group_by_frequency(filtered)
    print(f"\nFound {len(best_per_freq)} distinct frequencies in the range {FREQ_MIN}–{FREQ_MAX} kHz.")
    print("   (each shown with the lowest amplitude for that frequency)")

    # 6. Print the table to console
    for freq, amp, label in best_per_freq:
        print(f"   {freq:6.2f} kHz  |  Amplitude: {amp:8.2f}  |  {label}")

    # 7. Overall best (minimum amplitude) within the range
    overall_best = min(best_per_freq, key=lambda x: x[1])
    print(f"\nBest (minimum) amplitude in the range {FREQ_MIN}–{FREQ_MAX} kHz:")
    print(f"   Frequency:  {overall_best[0]:.2f} kHz")
    print(f"   Amplitude: {overall_best[1]:.2f}")
    print(f"   Parameter: {overall_best[2]}")

    # 8. Statistics
    print("\nStatistics for the grouped data:")
    print_statistics(best_per_freq)

    # 9. Export to CSV with dynamic filename
    output_dir = os.path.dirname(HTML_FILE)
    csv_filename = f"best_per_freq_{FREQ_MIN}_{FREQ_MAX}kHz.csv"
    csv_output = os.path.join(output_dir, csv_filename)
    export_csv(best_per_freq, csv_output)
    print(f"\nAll grouped data has been saved to '{csv_output}'.")

if __name__ == '__main__':
    main()