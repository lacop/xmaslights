import usb_cdc

# Enable USB CDC for REPL and STDIO (default is just console for REPL).
# We need to do this in boot.py.
usb_cdc.enable(console=True, data=True)
