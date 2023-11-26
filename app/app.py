import subprocess
import time
from os.path import abspath, dirname, join
import configparser
import json

from discord_webhook import DiscordWebhook, DiscordEmbed


last_change_path = join(dirname(abspath(__file__)), "last_change.ini")
config_path = join(dirname(abspath(__file__)), "config.ini")

class Change():
  def __init__(self, change_header, content):
    split = change_header.split(" ")
    self.num = split[1]
    self.date = split[3]
    self.time = split[4]
    self.user = split[6]
    self.content = content

class PerforceLogger():
	def __init__(self,webhook_url, repo):
		self.webhook_url = webhook_url
		self.repo = repo
		
	def p4_fetch(self, max):
		p4_changes = subprocess.Popen(f'p4 changes -t -m {max} -s submitted -e {self.read_num()+1} -l {self.repo}', stdout=subprocess.PIPE, shell=True)
		#Get the result from the p4 command
		return p4_changes.stdout.read().decode('ISO-8859-1')

	def save_num(self,number):
		"""Write the integer corresponding to the latest change in the dedicated file"""
		with open(last_change_path, 'w') as f:
			f.write('%d' % number)
			print("Latest change number overriden.")

	def read_num(self): #This function will return 0 in case the file is not readable
		"""Read the integer corresponding to the latest change from the dedicated file"""
		try:
			with open(last_change_path, 'r') as f:
				num_str = f.read()
				return int(num_str)
		except:
			return 0
			
	def check_post_changes(self):
		changes_as_str = self.p4_fetch(max=10)
		changes = self.regroup_changes(changes_as_str)
		
		for payload in reversed(changes):
			if(payload != ''):
				webhook = DiscordWebhook(url=self.webhook_url)
				user = payload.user.split("@")[0]
				embed = DiscordEmbed(title =f"`Change #{payload.num}`", description= f"```fix\n{payload.content.lstrip()}```", color = "51d1ec")
				embed.set_author(name=f"Committed by {user}")
				embed.add_embed_field(name="Time Committed", value= f"{payload.date} {payload.time} EST ", inline = False)
				webhook.add_embed(embed)
				response = webhook.execute()
			time.sleep(3)
		
	def regroup_changes(self, output):
		changes =[]

		if(len(output)>0):
			last_num_str = "" #this string will hold the first change number
			lines = output.splitlines() #split the strings by new line
			str_header = ""
			str_content_buffer = [] # this temporary buffer will contain each line of a change
			
			for l in lines:
				if(l.startswith('Change')): #If we see the word change (caracteristic of p4 changes), we close and open the buffer
					if(len(str_content_buffer) > 0): #Append the changes array with the last registered strings (closing change)
						changes.append(Change(str_header, ''.join(str_content_buffer)))
					else: # Only happens on first occurence: save the first change number as it is the most recent
						last_num_str = l.split(" ")[1]
					str_header = l
					str_content_buffer = [] # Start with a fresh buffer
				else: #Applies to other lines (content)
					str_content_buffer.append(l+"\n") #Add the current line
			# --- end of for loop ---
			
			#Last line closing
			changes.append(Change(str_header, ''.join(str_content_buffer)))
			
			# Also affect the last num
			if(last_num_str != ""): # Affect the last change number to the config file
				last_num = int(last_num_str)
				self.save_num(last_num)
		return changes

if __name__ == "__main__":
	config = configparser.ConfigParser()
	config.read(config_path)
	
	DISCORD_WEBHOOK_URL = config['Discord']['webhook']
	P4_TARGET = config['Perforce']['target']
	MAX_CHANGES = config.getint('ApplicationSettings','max_changes')

	logger = PerforceLogger(DISCORD_WEBHOOK_URL, P4_TARGET)
	logger.check_post_changes()
