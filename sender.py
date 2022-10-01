import multiprocessing
import threading

import random
import time
import sys

import checksum
import constants
from packet import *


class Sender:
    def __init__(self, name, fileName, senderToChannel, channelToSender): 
        self.name               = name # Name of the sender process
        self.fileName           = fileName # File from where packets is to be generated
        self.senderToChannel    = senderToChannel # Write head of the Sender to Channel pipe
        self.channelToSender    = channelToSender # Read of the Channel to Sender pipe
        self.packetType         = {'data' : 0, 'ack' : 1} # Defines the packet type
        self.dest               = self.chooseReceiverNumber() # Receiver node address
        self.seqNo              = 0 # Seqeunce number of the packet to be sent (0,1,0,1....)
        self.timeoutEvent       = threading.Event() # Needed for the timeout implementation
        self.endTransmission    = False # FLag to mark end of transmission
        self.receivedAck        = False # Flag to mark whether acknowledgement is received successfully



    #Function to choose the receiver for the current sender
    def chooseReceiverNumber(self):
        rec = 0 
        while(1):
            rec=int(input("Select a receiver for Sender {}: ".format(self.name+1)))

            if(rec>constants.TOT_RECEIVER or rec<=0):
                print("RECEIVER DOES NOT EXIST, PLEASE SELECT A VALID RECEIVER")
            else:
                rec = rec - 1
                break
        return rec

        
    # Function to get the file handle for input file
    def openFile(self, filename):
        try:
            file = open(filename, 'r')
        except IOError:
            sys.exit("FILE NON EXISTANT!")
        return file

    #Function to resend the current packet because acknowledgement is not received for it
    def resendCurrentPacket(self):
        self.senderToChannel.send(self.currentPacket)

    def checkAcknowledgement(self):
        time.sleep(0.1)
        while True:
            
            #Keep receiving packets till end of transmission is set true
            if not self.endTransmission: 
                packet = self.channelToSender.recv()
            else: 
                break
                
            #Check if it is an acknowledgement packet
            if packet.type == 1:
                if packet.checkForError():
                    if packet.seqNo == self.seqNo:
                        self.timeoutEvent.set()
                        print("[SENDER {}: ] THE LAST PACKET HAS BEEN SUCCESSFULLY RECEIVED AND ACKNOWLEDGED......".format(self.name+1))
                    else: 
                        self.timeoutEvent.clear()
                else:
                    self.timeoutEvent.clear()
            else: 
                self.timeoutEvent.clear()
            



    def sendPackets(self):
        time.sleep(0.1)
        start_time = time.time()
        print("!----------------------------------------------------------------------------------!")
        print("SENDER {} STARTS TRANSMISSION TO RECEIVER {}".format(self.name+1, self.dest+1))
        print("!----------------------------------------------------------------------------------!")
        
        file = self.openFile(self.fileName)
        byte = file.read(constants.DATA_PACK_SIZE)

        self.seqNo = 0
        countPackets = 0
        countTotalPackets = 0

        while byte:
            packet = Packet(self.packetType['data'], self.seqNo, byte, self.name, self.dest).makePacket()
            self.currentPacket = packet
            self.senderToChannel.send(packet)
            self.seqNo = (self.seqNo+1)%2

            countPackets += 1
            countTotalPackets += 1

            print("[SENDER {}: ] PACKET {} HAS BEEN SUCCESSFULLY TRANSMITTED.......".format(self.name+1, countPackets))
            
            #To check if acknowledgement is not received
            while not self.receivedAck: 
                self.timeoutEvent.wait(constants.SENDER_TIMEOUT)
                time.sleep(0.1)

                #To check if still event is not set
                if not self.timeoutEvent.isSet(): 
                    self.resendCurrentPacket()
                    countTotalPackets += 1
                    print("[SENDER {}: ] PACKET {} HAS BEEN RE-TRANSMITTED.......".format(self.name+1,countPackets))
                else: break
            self.timeoutEvent.clear()

            byte = file.read(constants.DATA_PACK_SIZE)
        
        #Now mark the end of the transmission as true
        self.endTransmission = True 
        file.close()
        total_time = time.time() - start_time
        averageRoundTime = total_time/countTotalPackets
        print("[SENDER {}: ] THE FINAL PACKET HAS BEEN SUCCESSFULLY RECEIVED AND ACKNOWLEDGED......".format(self.name+1))
        print("!---------------------------------SHOW STATS------------------------------------------!")
        print("\n______________________SENDER {}_________________________".format(self.name+1))
        print("\nTOTAL PACKETS SENT: {}\nTOTAL PACKETS REQUIRED FOR THE ENTIRE TRANSMISSION: {}\nTIME REQUIRED FOR THE ENTIRE TRANSMISSION: {}\nAVERAGE ROUND TRIP TIME FOR A PACKET: {}".format(countPackets, countTotalPackets,total_time,averageRoundTime))
        print("\n!-------------------------------------------------------------------------------------!")
        

    def startSending(self):
        
        sendingThread = threading.Thread(name="SendingThread", target=self.sendPackets)

        acknowledgementThread = threading.Thread(name='AcknowledgementThread', target=self.checkAcknowledgement)

        sendingThread.start()
        acknowledgementThread.start()

        sendingThread.join()
        acknowledgementThread.join()



