import zebra

def convert_to_zpl(imei):
    # ZPL template for a barcode
    zpl_template = f"""
    ^XA
    ^FX Third section with bar code.
    ^BY5,2,130
    ^FO100,250^BC^FD{IMEI}^FS
    ^FS

    ^XZ
    """
    return zpl_template

while True:
    IMEI = input("Scan the IMEI barcode: ")
    print(f"Scanned unit {IMEI}")
    try:
        zpl = convert_to_zpl(IMEI)
        
        # Create an instance of the Zebra printer
        z = zebra.Zebra()

        # List all connected Zebra printers
        printers = z.getqueues()
        print(f"Available printers: {printers}")

        # Set the desired printer (assuming the first one is the Zebra printer)
        z.setqueue(printers[0])
        z.output(zpl)
        # Print the ZPL label
        print("Printed Successfully")
        print("---------------------------------")
    except:
        print(f"Error occured printing unit {IMEI}")