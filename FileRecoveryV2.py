# FileRecoveryV2
# Making some modifications for readability

from math import ceil # ceiling function
from sys import argv # collect user arguments
import os # read directories
from binascii import a2b_hex # hex to binary
from shutil import move # move directories
import hashlib


# read file
fileName = argv[1]
print(fileName)
f = open(fileName, "rb")


# Read boot sector and get relevant information
def lEndInt(start, end):
    """ Converts Little Endian to Int"""
    sector = bootSector[start:end]
    asByte = bytes.fromhex(sector)
    asInt = int.from_bytes(asByte, "little")
    return asInt

bootSector = bytes.hex(f.read(512))

bytesPerSector = lEndInt(22,26)
sectorPerCluster = int(bootSector[26:28])
reservedSectors = lEndInt(28,32)
numberOfFats = int(bootSector[32:34])
sectorsPerFat = lEndInt(44,48)
sectorsBeforePartition = lEndInt(56,64)
numberOfSectors = lEndInt(64,70)


# Find the offset of the root directory
rootDirectorySectors = 32
rootDirectoryOffset = bytesPerSector * (reservedSectors + numberOfFats * sectorsPerFat) # 208896


f.seek(rootDirectoryOffset) # Go to the offset of the root directory
rootDirectory = bytes.hex(f.read(2*512)) # Read the root directory

# Store Information about the files
files = [[], [], [], [], []] # [[name], [extension], [File size], [start], [end]]
fileCount = 0 # number of files discovered
tempFile = rootDirectory[64:192] # file entry in the root directory
tempStart = rootDirectoryOffset + (rootDirectorySectors + reservedSectors) * bytesPerSector # 229376
junk = 0 # shift for files in the root directory that take up 64 bytes instead on 128


# Look through directory until it hits the trash
while (tempFile[64:72] != '5452415348'):
    
    # Get file size information
    tempSize = (int.from_bytes(bytes.fromhex(tempFile[120:128]), "little"))
    tempSectors = ceil(tempSize / bytesPerSector)
    tempEnd = tempSectors * bytesPerSector + tempStart

    # Get the name of the file
    tempName = tempFile[2:22] + tempFile[28:52]+tempFile[56:64]
    tempName = tempName.split('002e')[0].strip("00")
    tempName = bytes.fromhex((tempName))
    tempName = tempName.replace(b'\x00', b'').decode()

    # Get the extension of the file
    tempExt = bytes.fromhex(tempFile[80:86]).decode()
    
    # Add information to files list
    files[0].append(tempName)
    files[1].append(tempExt)
    files[2].append(tempSectors)
    files[3].append(tempStart)
    files[4].append(tempEnd)

    # Load the next file
    fileCount += 1
    tempStart += (ceil(tempSectors/sectorPerCluster)* sectorPerCluster)*bytesPerSector
    tempFile = rootDirectory[64 + 64 * junk + fileCount * 128:192 + 64 * junk + fileCount * 128]
    
    # Account for empty half entry
    if (tempFile[28: 52] == "ffffffffffffffffffffffff"):
        junk += 1
        tempFile = rootDirectory[64 + 64 * junk + fileCount * 128:192 + 64 * junk + fileCount * 128]

# Format Output
print(f'The disk image contains {fileCount} files')

currentDirectory = os.getcwd()
recoveryFolder = f'{currentDirectory}/RecoveredFiles'

# Create the folder /RecoveredFiles if it does not already exist
if not os.path.exists(recoveryFolder):
    os.mkdir(recoveryFolder)

for file in range(fileCount):
    
    # unpack file information
    tempName = files[0][file]
    tempExt = files[1][file]
    tempName = f'{tempName}.{tempExt}'
    tempSectors = files[2][file]
    tempStart = files[3][file]
    tempEnd = files[4][file]

    print(f'{tempName}, Start Offset: {hex(tempStart)}, End Offset: {hex(tempEnd)}')
    

    f.seek(tempStart) # Jump to start of the file
    fileHex = bytes.hex(f.read(tempSectors*bytesPerSector)) # reads the file
    fileData = a2b_hex(fileHex.strip()) # hex to binary
    #Get the SHA-256 hash of the file
    readable_hash = hashlib.sha256(fileData).hexdigest()
    print('SHA-256: ' + readable_hash + '\n')
    # Write binary data into the file
    with open(tempName, 'wb') as image:
        image.write(fileData)
    
    # Moves the file into the directory
    move(f'{currentDirectory}/{tempName}',f'{recoveryFolder}/{tempName}')

f.close() # done, close the file.
print("Recovered files are located in ~/RecoveredFiles")
