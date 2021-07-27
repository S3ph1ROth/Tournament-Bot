import os
import json
import discord
from dotenv import load_dotenv
from graphqlclient import GraphQLClient
import requests

#klasa za meceve sa svim potrebnim informacijama (self-explanatory)
class Match:
  def __init__(self, round, player1, player2, player1Country, player2Country, player1DiscordId, player2DiscordId):
    self.round = round
    self.player1 = player1
    self.player2 = player2
    self.player1Country = player1Country
    self.player2Country = player2Country
    self.player1DiscordId = player1DiscordId
    self.player2DiscordId = player2DiscordId


#ovo pokrece bota sa lokala, pip install dotenv za instalaciju biblioteke
load_dotenv()
#inicijalizacija dictionary-a sa mecevima
matches = {}
#discord bot konekcija
client = discord.Client()
botToken = os.getenv('BOTTOKEN')
#request za zastave, mozda trebas da uradis pip install requests, ali nisam siguran
response = requests.get("https://flagcdn.com/en/codes.json")
countries = response.json()

#funckija za inicijalizaciju turnira, uzme se iz url-a bracketId (npr u https://smash.gg/tournament/sol-strive-online-league-by-fgc-serbia/event/strive-1v1/brackets/955365/1517331/ je 955365 bracketId)
#kada uzme bracketId na osnovu njega pravi request da uzme broj meceva u fazi (kod nas ceo bracket), pa onda pravi request da uzme sve informacije za meceve
def initTournament(url):

  #@Darkwing promeni na svoj smash.gg token ili ostavi moj, svejedno je (kliknes na svoj profil i otvoris developer settings i tu generises token)
  smashggToken = os.getenv('SMASHGGTOKEN')
  #parsiranje url-a da se uzme bracketId
  bracket = url.split('/')
  if bracket[-1] != '':
    bracketId = bracket[-2]
  else:
    bracketId = bracket[-3]
  #inicijalizacija graphQL requesta, instaliras biblioteku sa pip install graphqlclient
  apiVersion = 'alpha'
  apiClient = GraphQLClient('https://api.smash.gg/gql/' + apiVersion)
  apiClient.inject_token('Bearer ' + smashggToken)
  getMatchNumber = apiClient.execute('''
      query PhaseTotal($bracketId: ID!) {
          phase(id: $bracketId) {
              sets{
                  pageInfo {
                      total
                  } 
              }
          }
      }
  ''',
  {
      "bracketId": bracketId
  })

  matchNum = json.loads(getMatchNumber)

  getAllMatchesQuery = apiClient.execute('''
  query TournamentInfo($bracketId: ID!, $page: Int!, $perPage: Int!) {
    phase(id: $bracketId) {
      id
      name
      sets(
          page: $page
          perPage: $perPage
          sortType: STANDARD
      ){
        pageInfo {
            total
        }
        nodes {
          id
          fullRoundText
          identifier
          slots {
            id
            entrant {
              id
              name
              participants{
                  id
                  gamerTag
                  user{
                    id
                    authorizations(
                      types:DISCORD
                    ){
                      externalId
                      externalUsername
                    }
                    location{
                      id
                      country
                      countryId
                    }
                  }
                }
            }
          }
        }
      }
    }
  }
  ''',
  {
      "bracketId":bracketId,
      "page":1,
      "perPage":matchNum["data"]["phase"]["sets"]["pageInfo"]["total"]
  })

  getAllMatches = json.loads(getAllMatchesQuery)

  #upisivanje podataka u dictionary
  for match in getAllMatches["data"]["phase"]["sets"]["nodes"]:
    id = match["identifier"].lower()
    round = match["fullRoundText"]
    player1 = match['slots'][0]['entrant']['name']
    player2 = match['slots'][1]['entrant']['name']
    player1Country = match['slots'][0]['entrant']['participants'][0]['user']['location']['country']
    if player1Country is None:
      player1Country = "N/A"
    
    player2Country = match['slots'][1]['entrant']['participants'][0]['user']['location']['country']
    if player2Country is None:
      player2Country = "N/A"
    if match['slots'][0]['entrant']['participants'][0]['user']['authorizations']:
        player1DiscordId = match['slots'][0]['entrant']['participants'][0]['user']['authorizations'][0]['externalId']
    else:
        player1DiscordId = match['slots'][0]['entrant']['name']
    if match['slots'][1]['entrant']['participants'][0]['user']['authorizations']:
        player2DiscordId = match['slots'][1]['entrant']['participants'][0]['user']['authorizations'][0]['externalId']
    else:
        player2DiscordId = match['slots'][1]['entrant']['name']
    matches[id] = Match(round, player1, player2, player1Country, player2Country, player1DiscordId, player2DiscordId)

#funkcija da se iz country polja izvuce country code za API i da ga pretvori u img tag za upis (slabs radi i samo sa img-om, ne mora da se pise ceo html)
def convertToCountryCode(countryName, countries):

  if countryName == "N/A":
    return "N/A"
    
  for key, value in countries.items():
    if value == countryName:
        return '<img src="https://www.countryflags.io/' + key + '/shiny/64.png">'

#bot slusa eventove, ovo je cim se upali i konektuje za server
@client.event
async def on_ready():
  print('We have logged in as {0.user}'.format(client))
  
#event za slusanje poruka
@client.event
async def on_message(message):
  if message.author == client.user:
    return
  
  #inicijalizacija turnira ako je komanda $url link_ka_bracketu
  if message.content.startswith("$url"):
    url = message.content.split(' ')[1]
    initTournament(url)
    await message.channel.send("Bracket initialized")

  #ispis podataka u fajlove i tagovanje sledecih igraca za stream
  for keys in matches.keys():
    if(message.content.lower()[1:] == keys.lower()):
      key = message.content[1:]
      f = open("round.txt", "w")
      f.write(matches[key].round)
      f.close()
      f = open("player1.txt", "w")
      f.write(matches[key].player1)
      f.close()
      f = open("player1country.html", "w")
      countryHtml = convertToCountryCode(matches[key].player1Country, countries)
      f.write(countryHtml)
      f.close()
      f = open("player2.txt", "w")
      f.write(matches[key].player2)
      f.close()
      f = open("player2country.html", "w")
      countryHtml = convertToCountryCode(matches[key].player2Country, countries)
      f.write(countryHtml)
      f.close()
      await message.channel.send("Round is " + matches[key].round)
      await message.channel.send("Player 1 is " + matches[key].player1)
      await message.channel.send("Player 2 is " + matches[key].player2)
      await message.channel.send("On stream <@" + matches[key].player1DiscordId + '> <@' + matches[key].player2DiscordId + '>')
      await message.channel.send("Files updated")

  #komanda za swapovanje igraca za slucaj da zatreba, da ne mora rucno da se radi
  if(message.content.startswith("$swap")):
    f = open("player1.txt", "r")
    player2 = f.read()
    f.close()
    f = open("player2.txt", "r")
    player1 = f.read()
    f.close()
    f = open("player1.txt", "w")
    f.write(player1)
    f.close()
    f = open("player2.txt", "w")
    f.write(player2)
    f.close()
    await message.channel.send("Player 1 is now " + player1 + " and player 2 is now " + player2)
  
  #uputstvo kako koristiti bota za bota mikija :D
  if(message.content.startswith("$help")):
    await message.channel.send('''
    HOW TO USE:
    When starting the tournament use the $url command by typing in the channel: $url link_to_the_bracket
    Then just type $match_id (i.e. $A, $B, $AA, $AE...)
    If you need to swap the player names just type in $swap
    ''')

client.run(botToken)