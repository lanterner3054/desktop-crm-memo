"""Extract qwebchannel.js from Qt resources to a real file."""
import sys
from PySide6.QtCore import QFile, QIODevice, QCoreApplication

app = QCoreApplication(sys.argv)
f = QFile(":/qtwebchannel/qwebchannel.js")
if not f.open(QIODevice.ReadOnly):
    print("FAILED to open qrc:/qtwebchannel/qwebchannel.js")
    sys.exit(1)
data = bytes(f.readAll())
f.close()
out = sys.argv[1] if len(sys.argv) > 1 else "qwebchannel.js"
with open(out, "wb") as fp:
    fp.write(data)
print(f"wrote {len(data)} bytes to {out}")
