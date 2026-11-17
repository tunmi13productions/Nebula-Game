import sys, lief
b = lief.MachO.parse(sys.argv[1]).at(0)
print("cpu", b.header.cpu_type)
for c in b.commands:
    if c.command.name.startswith("ENCRYPTION"):
        print("encryption cryptid", c.crypt_id, "off", c.crypt_offset, "size", c.crypt_size)
for s in b.sections:
    print("section", s.segment_name, s.name, hex(s.virtual_address), s.size)
for l in b.libraries:
    print("lib", l.name)
