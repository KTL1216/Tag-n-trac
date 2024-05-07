# Open the input file in read mode and the output file in write mode
with open('input.txt', 'r') as infile, open('output.txt', 'w') as outfile:
    # Skip the header line in the input file
    next(infile)
    # Process each line in the input file
    for line in infile:
        # Check if the line is not just a newline and contains enough commas
        if line.strip() and line.count(',') >= 2:
            try:
                # Split the line by comma to extract fields
                sn, imei, iccid = line.strip().split(',')
                # Write the SN value followed by a newline to the output file
                if sn != "SN":
                    outfile.write(sn + '\n')
            except ValueError as e:
                print(f"Error processing line: {line.strip()} -> {e}")
        else:
            print(f"Skipping invalid line: {line.strip()}")

print("The SN values have been extracted to 'output.txt'.")
