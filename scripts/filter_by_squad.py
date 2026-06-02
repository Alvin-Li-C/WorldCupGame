"""
Filter WCQ player stats to only include players in the 2026 World Cup 26-man squads.
Uses Sky Sports squad data parsed from the article.
"""
import os
import sys
import json
import re
import unicodedata

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Sky Sports squad data - pasted from the article
SKY_SPORTS_TEXT = r"""
## Group A squads

### Mexico

Goalkeepers: Carlos Acevedo (Santos Laguna), Guillermo Ochoa (AEL Limassol), Raul Rangel (Chivas).

Defenders: Edson Alvarez (Fenerbahce), Israel Reyes (America), Jesus Gallardo (Toluca), Johan Vasquez (Genoa), Jorge Sanchez (PAOK), Mateo Chavez (AZ Alkmaar).

Midfielders: Alvaro Fidalgo (Real Betis), Brian Gutierrez (Chivas), Erik Lira (Cruz Azul), Gilberto Mora (Tijuana), Luis Romo (Chivas), Obed Vargas (Atletico Madrid), Orbelin Pineda (AEK).

Forwards: Alexis Vega (Toluca), Armando Gonzalez (Chivas), Cesar Huerta (Anderlecht), Guillermo Martinez (Pumas), Julian Quinones (Al Qadisiyah), Raul Jimenez (Fulham), Santiago Gimenez (AC Milan).

### South Africa

Goalkeepers: Sipho Chaine (Orlando Pirates), Ricardo Goss (Siwele), Ronwen Williams (Mamelodi Sundowns).

Defenders: Aubrey Modiba (Mamelodi Sundowns), Khuliso Mudau (Mamelodi Sundowns), Nkosinathi Sibisi (Orlando Pirates), Mbekezeli Mbokazi (Chicago Fire), Ime Okon (Hannover), Samukele Kabini (Molde), Khulumani Ndamane (Mamelodi Sundowns), Thabang Matuludi (Polokwane City), Kamogelo Sebelebele (Orlando Pirates), Bradley Cross (Kaizer Chiefs), Olwethy Makhanya (Philadelphia Union).

Midfielders: Teboho Mokoena (Mamelodi Sundowns), Sphephelo Sithole (Tondela), Thalente Mbatha (Orlando Pirates), Jayden Adams (Mamelodi Sundowns).

Forwards: Themba Zwane (Mamelodi Sundowns), Lyle Foster (Burnley), Evidence Makgopa (Orlando Pirates), Oswin Appollis (Orlando Pirates), Iqraam Rayners (Mamelodi Sundowns), Relebohile Mofokeng (Orlando Pirates), Thapelo Maseko (AEL Limassol), Tshepang Moremi (Orlando Pirates).

### South Korea

Goalkeepers: Hyeon-Woo Jo (Ulsan), Seung-Gyu Kim (FC Tokyo), Bum-Keun Song (Jeonbuk).

Defenders: Moon-Hwan Kim (Daejeon), Min-Jae Kim (Bayern Munich), Tae-Hyon Kim (Kashima Antlers), Jin-Seob Park (Zhejiang), Young-Woo Seol (Red Star Belgrade), Jens Castrop (Borussia Monchengladbach), Ki-Hyuk Lee (Gangwon), Tae-Seok Lee (Austria Wien), Han-Beom Lee (Midtjylland), Yu-Min Cho (Sharjah).

Midfielders: Jin-Gyu Kim (Jeonbuk), Jun-Ho Bae (Stoke), Seung-Ho Paik (Birmingham), Hyun-Jun Yang (Celtic), Ji-Sung Eom (Swansea), Kang-In Lee (Paris Saint-Germain), Dong-Gyeong Lee (Ulsan), Jae-Sung Lee (Mainz), In-Beom Hwang (Feyenoord), Hee-Chan Hwang (Wolves).

Forwards: Heung-Min Son (LAFC), Hyeon-Gyu Oh (Besiktas), Gue-Sung Cho (Midtjylland).

### Czech Republic

Goalkeepers: Lukas Hornicek (Braga), Matej Kovar (PSV Eindhoven), Jindrich Stanek (Slavia Prague).

Defenders: Vladimir Coufal (Hoffenheim), David Doudera (Slavia Prague), Tomas Holes (Slavia Prague), Robin Hranac (Hoffenheim), Stepan Chaloupek (Slavia Prague), David Jurasek (Slavia Prague), Ladislav Krejci (Wolverhampton), Jaroslav Zeleny (Sparta Prague), David Zima (Slavia Prague).

Midfielders: Lukas Cerv (Viktoria Plzen), Vladimir Darida (Hradec Kralove), Lukas Provod (Slavia Prague), Michal Sadilek (Slavia Prague), Hugo Sochurek (Sparta Prague), Alexandr Sojka (Viktoria Plzen), Tomas Soucek (West Ham), Pavel Sulc (Olympique Lyonnais), Denis Visinsky (Viktoria Plzen).

Forwards: Adam Hlozek (Hoffenheim), Tomas Chory (Slavia Prague), Mojmir Chytil (Slavia Prague), Jan Kuchta (Sparta Prague), Patrik Schick (Bayer Leverkusen).

## Group B squads

### Canada

Goalkeepers: Maxime Crepeau (Orlando City), Owen Goodman (Barnsley), Dayne St. Clair (Inter Miami).

Defenders: Moise Bombito (Nice), Derek Cornelius (Rangers), Alphonso Davies (Bayern Munich), Luc de Fougerolles (Dender EH), Alistair Johnston (Celtic), Alfie Jones (Middlesbrough), Richie Laryea (Toronto), Niko Sigur (Hajduk Split), Joel Waterman (Chicago Fire).

Midfielders: Ali Ahmed (Norwich), Tajon Buchanan (Villarreal), Mathieu Choiniere (LAFC), Stephen Eustaquio (LAFC), Marcelo Flores (Tigres UANL), Ismael Kone (Sassuolo), Liam Millar (Hull), Jonathan Osorio (Toronto), Nathan-Dylan Saliba (Anderlecht), Jacob Shaffelburg (LAFC).

Forwards: Jonathan David (Juventus), Promise David (Union Saint-Gilloise), Cyle Larin (Southampton), Tani Oluwaseyi (Villarreal).

### Bosnia-Herzegovina

Goalkeepers: Nikola Vasilj (St Pauli), Martin Zlomislic (Rijeka), Osman Hadzikic (Slaven Belupo).

Defenders: Sead Kolasinac (Atalanta), Amar Dedic (Benfica), Nihad Mujakic (Gaziantep), Nikola Katic (Schalke), Tarik Muharemovic (Sassuolo), Stjepan Radeljic (Rijeka), Dennis Hadzikadunic (Sampdoria), Nidal Celik (Lens).

Midfielders: Amir Hadziahmetovic (Hull), Ivan Sunjic (Pafos), Ivan Basic (Astana), Dzenis Burnic (Karlsruher), Ermin Mahmic (Slovan Liberec), Benjamin Tahirovic (Brondby), Amar Memic (Viktoria Plzen), Armin Gigovic (Young Boys), Kerim Alajbegovic (RB Salzburg), Esmir Bajraktarevic (PSV).

Forwards: Ermedin Demirovic (Stuttgart), Jovo Lukic (Universitatea Cluj), Samed Bazdar (Jagiellonia Bialystok), Haris Tabakovic (Borussia Monchengladbach), Edin Dzeko (Schalke).

### Qatar

Goalkeepers: Salah Zakaria (Al Duhail), Mahmoud Abunada (Al Rayyan), Meshaal Barsham (Al Sadd).

Defenders: Hashmi Hussein (Al Arabi), Ayoub Alawi (Al Gharafa), Boualem Khoukhi (Al Sadd), Pedro Miguel (Al Sadd), Issa Laaye (Al Arabi), Lucas Mendes (Al Wakrah), Sultan Al-Brake (Al Duhail), Homam Al-Amin (Cultural Leonesa).

Midfielders: Mohammed Al-Manai (Al Shamal), Jassem Jaber (Al Arabi), Karim Boudiaf (Al-Duhail), Ahmed Fathi (Al Arabi), Abdulaziz Hatem (Al Rayyan), Assim Madibo (Al Wakrah).

Forwards: Tahseen Mohammed (Al Duhail), Edmilson Junior (Al Duhail), Almoez Ali (Al Duhail), Akram Afif (Al Sadd), Mohammed Muntari (Al Gharafa), Youssef Abdulrazzaq (Al Wakrah), Ahmed Alaa (Al Rayyan), Hassan Al-Haydos (Al Sadd), Ahmed Al-Janahi (Al Gharafa).

### Switzerland

Goalkeepers: Marvin Keller (Young Boys), Gregor Kobel (Borussia Dortmund), Yvon Mvogo (Lorient).

Defenders: Manuel Akanji (Inter Milan), Aurele Amenda (Eintracht Frankfurt), Eray Comert (Valencia), Nico Elvedi (Borussia Monchengladbach), Luca Jaquez (Stuttgart), Miro Muheim (Hamburg), Ricardo Rodriguez (Real Betis), Silvan Widmer (Mainz).

Midfielders: Michel Aebischer (Pisa), Christian Fassnacht (Young Boys), Remo Freuler (Bologna), Ardon Jashari (AC Milan), Johan Manzambi (Freiburg), Fabian Rieder (Augsburg), Djibril Sow (Sevilla), Ruben Vargas (Sevilla), Granit Xhaka (Sunderland), Denis Zakaria (Monaco).

Forwards: Zeki Amdouni (Burnley), Breel Embolo (Rennes), Cedric Itten (Fortuna Dusseldorf), Dan Ndoye (Nottingham Forest), Noah Okafor (Leeds).

## Group C squads

### Brazil

Goalkeepers: Alisson (Liverpool), Ederson (Fenerbahce), Weverton (Gremio).

Defenders: Marquinhos (Paris Saint-Germain), Gabriel (Arsenal), Bremer (Juventus), Ibanez (Al Ahli), Leo Pereira (Flamengo), Wesley (Roma), Danilo (Flamengo), Alex Sandro (Flamengo), Douglas Santos (Zenit Saint Petersburg).

Midfielders: Casemiro (Manchester United), Bruno Guimaraes (Newcastle), Fabinho (Al Ittihad), Danilo (Botafogo), Lucas Paqueta (Flamengo).

Forwards: Vinicius Junior (Real Madrid), Raphinha (Barcelona), Matheus Cunha (Manchester United), Luiz Henrique (Zenit Saint Petersburg), Igor Thiago (Brentford), Endrick (Real Madrid), Gabriel Martinelli (Arsenal), Rayan (Bournemouth), Neymar (Santos).

### Morocco

Goalkeepers: Yassine Bounou (Al Hilal), Munir Mohamedi (RS Berkane), Ahmed Tagnaouti (Royal Armed Forces).

Defenders: Noussair Mazraoui (Manchester United), Anass Salah-Eddine (PSV), Youssef Belammari (Al Ahly), Nayef Aguerd (Marseille), Chadi Riad (Crystal Palace), Issa Diop (Fulham), Redouane Halhal (KV Mechelen), Achraf Hakimi (PSG), Zakaria El Ouahdi (Genk).

Midfielders: Samir El Mourabet (Strasbourg), Ayyoub Bouaddi (Lille), Neil El Aynaoui (Roma), Sofyan Amrabat (Real Betis), Azzedine Ounahi (Girona), Bilal El Khannouss (Stuttgart), Ismael Saibari (PSV).

Forwards: Abdessamad Ezzalzouli (Real Betis), Chemsdine Talbi (Sunderland), Soufiane Rahimi (Al Ain), Ayoub El Kaabi (Olympiacos), Brahim Diaz (Real Madrid), Yassine Gessime (Strasbourg), Ayoub Amaimouni-Echghouyabe (Eintracht Frankfurt).

### Haiti

Goalkeepers: Johnny Placide (Bastia), Alexandre Pierre (Sochaux), Josue Duverger (FC Cosmos Koblenz).

Defenders: Carlens Arcus (Angers), Wilguens Pauguain (Zulte Waregem), Duke Lacroix (Colorado Springs), Martin Experience (Nancy), Jean-Kevin Duverne (Gent), Ricardo Ade (LDU Quito), Hannes Delcroix (Lugano), Keeto Thermoncy (Young Boys).

Midfielders: Leverton Pierre (Vizela), Carl-Fred Sainthe (El Paso Locomotive), Jean-Jacques Danley (Philadelphia Union), Jean-Ricner Bellegarde (Wolves), Pierre Woodenski (Violette), Dominique Simon (Tatran Presov).

Forwards: Louicius Deedson (Dallas), Ruben Providence (Almere City), Josue Casimir (Auxerre), Derrick Etienne (Toronto), Wilson Isidor (Sunderland), Duckens Nazon (Esteghlal), Frantzdy Pierrot (Caykur Rizespor), Yassin Fortune (Vizela), Lenny Joseph (Ferencvaros).

### Scotland

Goalkeepers: Craig Gordon (Hearts), Angus Gunn (Nottingham Forest), Liam Kelly (Rangers).

Defenders: Grant Hanley (Hibernian), Jack Hendry (Al Etiffaq), Aaron Hickey (Brentford), Dom Hyam (Wrexham), Scott McKenna (Dinamo Zagreb), Nathan Patterson (Everton), Anthony Ralston (Celtic), Andy Robertson (Liverpool), John Souttar (Rangers), Kieran Tierney (Celtic).

Midfielders: Ryan Christie (Bournemouth), Findlay Curtis (Rangers), Lewis Ferguson (Bologna), Ben Gannon-Doak (Bournemouth), Tyler Fletcher (Man Utd), John McGinn (Aston Villa), Kenny McLean (Norwich), Scott McTominay (Napoli).

Forwards: Che Adams (Torino), Lyndon Dykes (Charlton), George Hirst (Ipswich), Lawrence Shankland (Rangers), Ross Stewart (Southampton).

## Group D squads

### USA

Goalkeepers: Chris Brady (Chicago Fire), Matt Freese (New York City FC), Matt Turner (New England Revolution).

Defenders: Max Arfsten (Columbus Crew), Sergino Dest (PSV), Alex Freeman (Villarreal), Mark McKenzie (Toulouse), Tim Ream (Charlotte FC), Chris Richards (Crystal Palace), Antonee Robinson (Fulham), Miles Robinson (FC Cincinnati), Joe Scally (Borussia Monchengladbach), Auston Trusty (Celtic).

Midfielders: Tyler Adams (Bournemouth), Sebastian Berhalter (Vancouver Whitecaps), Weston McKennie (Juventus), Gio Reyna (Borussia Monchengladbach), Cristian Roldan (Seattle Sounders), Malik Tillman (Bayer Leverkusen).

Forwards: Brenden Aaronson (Leeds), Folarin Balogun (Monaco), Ricardo Pepi (PSV), Christian Pulisic (AC Milan), Tim Weah (Marseille), Haji Wright (Coventry), Alejandro Zendejas (Club America).

### Paraguay

Goalkeepers: Roberto Junior Fernandez (Cerro Porteno), Orlando Gill (San Lorenzo), Gaston Olveira (Olimpia).

Defenders: Omar Alderete (Sunderland), Junior Alonso (Atletico Mineiro), Fabian Balbuena (Gremio), Juan Jose Caceres (Dinamo Moscow), Jose Canale (Lanus), Gustavo Gomez (Palmeiras), Alexandro Maidana (Talleres), Gustavo Velazquez (Cerro Porteno).

Midfielders: Damian Bobadilla (Sao Paulo), Gustavo Caballero (Portsmouth), Andres Cubas (Vancouver Whitecaps), Matias Galarza (Atlanta United), Diego Gomez (Brighton), Mauricio Magalhaes (Palmeiras), Briaian Ojeda (Orlando City), Alejandro Romero (Al Ain).

Forwards: Miguel Almiron (Atlanta United), Gabriel Avalos (Independiente), Alex Arce (Independiente Rivadavia), Julio Enciso (Strasbourg), Isidro Pitta (Bragantino), Antonio Sanabria (Cremonese), Ramon Sosa (Palmeiras).

### Australia

Goalkeepers: Ryan (Levante), Izzo (Randers), Beach (Melbourne City).

Defenders: Behich (Melbourne City), Bos (Feynoord), Burgess (Swansea City), Circati (Parma), Degenek (APOEL), Geria (Albirex Niigata), Herrington (Colorado Rapids), Italiano (Grazer), Souttar (Leicester), Trewin (New York City).

Midfielders: Devlin (Heart of Midlothian), Hrustic (Heracles Almelo), Irvine (St Pauli), Metcalfe (St Pauli), Okon-Englster (Sydney), O'Neill (New York City).

Forwards: Irankunda (Watford), Leckie (Melbourne City), Mabil (Castellon), Toure (Norwich), Velupilly (Melbourne City), Volpato (Sassuolo), Tete Yengi (Livingston).

### Turkey

Goalkeepers: Ugurcan Cakir (Galatasaray), Altay Bayindir (Man Utd), Mert Gunok (Besiktas).

Defenders: Ferdi Kadioglu (Brighton), Merih Demiral (Al Ahli), Zeki Celik (Roma), Ozan Kabak (Hoffenheim), Mert Muldur (Fenerbahce), Abdulkerim Bardakci (Galatasaray), Eren Elmali (Galatasaray), Caglar Soyuncu (Fenerbahce), Samet Akaydin (Rizespor).

Midfielders: Arda Guler (Real Madrid), Can Uzun (Eintracht Frankfurt), Orkun Kokcu (Besiktas), Hakan Calhanoglu (Inter), Ismail Yuksek (Fenerbahce), Kaan Ayhan (Galatasaray), Salih Ozcan (Borussia Dortmund).

Forwards: Kenan Yildiz (Juventus), Baris Alper Yilmaz (Galatasaray), Kerem Akturkoglu (Fenerbahce), Yunus Akgun (Galatasaray), Oguz Aydin (Fenerbahce), Deniz Gul (Porto), Irfan Can Kahveci (Fenerbahce).

## Group E squads

### Germany

Goalkeepers: Oliver Baumann (Hoffenheim), Manuel Neuer (Bayern Munich), Alexander Nubel (Bayern Munich).

Defenders: Waldemar Anton (Borussia Dortmund), Nathaniel Brown (Eintracht Frankfurt), David Raum (RB Leipzig), Antonio Rudiger (Real Madrid), Nico Schlotterbeck (Borussia Dortmund), Jonathan Tah (Bayern Munich), Malick Thiaw (Newcastle).

Midfielders: Pascal Gross (Brighton), Joshua Kimmich (Bayern Munich), Felix Nmecha (Borussia Dortmund), Aleksandar Pavlovic (Bayern Munich), Angelo Stiller (Stuttgart), Leon Goretzka (Bayern Munich), Florian Wirtz (Liverpool), Jamie Leweling (Stuttgart).

Forwards: Maximilian Beier (Borussia Dortmund), Kai Havertz (Arsenal), Lennart Karl (Bayern Munich), Jamal Musiala (Bayern Munich), Leroy Sane (Galatasaray), Deniz Undav (Stuttgart), Nick Woltemade (Newcastle).

### Curacao

Goalkeepers: Tyrick Bodak (SC Telstar), Trevor Doornbusch (VVV-Venlo), Eloy Room (Miami FC).

Defenders: Riechedly Bazoer (Konyaspor), Joshua Brenet (Kayserispor), Roshon van Eijma (RKC Waalwijk), Sherel Floranus (PEC Zwolle), Deveron Fonville (NEC Nijmegen), Jurien Gaari (Abha Club), Armando Obispo (PSV), Shurandy Sambo (Sparta Rotterdam).

Midfielders: Juninho Bacuna (FC Volendam), Leandro Bacuna (Igdir), Livano Comenencia (FC Zurich), Kevin Felida (FC Den Bosch), Ar'Jany Martha (Rotherham), Tyrese Noslin (SC Telstar), Godfried Roemeratoe (RKC Waalwijk).

Forwards: Jeremy Antonisse (AE Kifisia), Tahith Chong (Sheffield United), Kenji Gorre (Maccabi Haifa), Sontje Hansen (Middlesbrough), Gervane Kastaneer (Terengganu FC), Brandley Kuwas (FC Volendam), Jurgen Locadia (Miami FC), Jearl Margaritha (SK Beveren).

### Ivory Coast

Goalkeepers: Yahia Fofana (Caykur Rizespor), Mohamed Kone (Charleroi), Alban Lafont (Panathinaikos).

Defenders: Emmanuel Agbadou (Besiktas), Clement Akpa (Auxerre), Ousmane Diomande (Sporting), Guela Doue (Strasbourg), Ghislain Konan (Gil Vicente), Odilon Kossounou (Atalanta), Evan Ndicka (Roma), Wilfried Singo (Galatasaray).

Midfielders: Seko Fofana (Porto), Parfait Guiagon (Charleroi), Christ Inao Oulai (Trabzonspor), Franck Kessie (Al Ahli), Ibrahim Sangare (Nottingham Forest), Jean-Michael Seri (Maribor).

Forwards: Simon Adingra (Monaco), Ange-Yoan Bonny (Inter Milan), Amad Diallo (Man Utd), Oumar Diakite (Cercle Brugge), Yan Diomande (RB Leipzig), Evann Guessand (Aston Villa), Nicolas Pepe (Villarreal), Bazoumana Toure (Hoffenheim), Elye Wahi (Nice).

### Ecuador

Goalkeepers: Hernan Galindez (Huracan), Moises Ramirez (Kifisia), Gonzalo Valle (LDU Quito).

Defenders: Piero Hincapie (Arsenal), Willian Pacho (PSG), Pervis Estupinan (AC Milan), Felix Torres (Internacional), Joel Ordonez (Club Brugge), Jackson Porozo (Tijuana), Angelo Preciado (Atletico Mineiro).

Midfielders: Moises Caicedo (Chelsea), Alan Franco (Atletico Mineiro), Kendry Paez (River Plate, on loan from Chelsea), Pedro Vite (UNAM), Jordy Alcivar (Independiente del Valle), Denil Castillo (Midtjylland), Yaimar Medina (Genk).

Forwards: Enner Valencia (Pachuca), Kevin Rodriguez (Union Saint-Gilloise), Jordy Caicedo (Huracan), Nilson Angulo (Sunderland), Anthony Valencia (Antwerp), Jeremy Arevalo (Stuttgart).

## Group F squads

### Netherlands

Goalkeepers: Bart Verbruggen (Brighton), Mark Flekken (Bayer Leverkusen), Robin Roefs (Sunderland).

Defenders: Virgil van Dijk (Liverpool), Jan Paul van Hecke (Brighton), Nathan Ake (Man City), Micky van de Ven (Tottenham), Denzel Dumfries (Inter Milan), Jorrel Hato (Chelsea), Jurrien Timber (Arsenal).

Midfielders: Frenkie de Jong (Barcelona), Tijjani Reijnders (Man City), Justin Kluivert (Bournemouth), Quinten Timber (Marseille), Teun Koopmeiners (Juventus), Ryan Gravenberch (Liverpool), Marten de Roon (Atalanta), Guus Til (PSV), Mats Weiffer (Brighton).

Forwards: Cody Gakpo (Liverpool), Donyell Malen (Roma), Brian Brobbey (Sunderland), Noa Lang (Galatasaray/Napoli), Memphis Depay (Corinthians), Wout Weghorst (Ajax), Crysencio Summerville (West Ham).

### Japan

Goalkeepers: Tomoki Hayakawa (Kashima Antlers), Keisuke Osako (Sanfrecce Hiroshima), Zion Suzuki (Parma).

Defenders: Yuto Nagatomo (FC Tokyo), Shogo Taniguchi (Sint-Truiden), Ko Itakura (Ajax), Tsuyoshi Watanabe (Feyenoord), Takehiro Tomiyasu (Ajax), Hiroki Ito (Bayern Munich), Ayumu Seko (Le Havre), Yukinari Sugawara (Werder Bremen/Southampton), Junosuke Suzuki (Copenhagen).

Midfielders: Wataru Endo (Liverpool), Junya Ito (Genk), Daichi Kamada (Crystal Palace), Koki Ogawa (NEC Nijmegen), Daizen Maeda (Celtic), Ritsu Doan (Eintracht Frankfurt), Ao Tanaka (Leeds), Kaishu Sano (Mainz), Takefusa Kubo (Real Sociedad).

Forwards: Ayase Ueda (Feyenoord), Keito Nakamura (Reims), Ito Suzuki (Freiburg), Kento Shiode (Wolfsburg), Keisuke Goto (Sint-Truiden).

### Sweden

Goalkeepers: Viktor Johansson (Stoke), Kristoffer Nordfeldt (AIK), Jacob Widell Zetterstrom (Derby).

Defenders: Hjalmar Ekdal (Burnley), Gabriel Gudmundsson (Leeds), Isak Hien (Atalanta), Emil Holm (Juventus), Gustaf Lagerbielke (Braga), Victor Lindelof (Aston Villa), Erik Smith (St Pauli), Carl Starfelt (Celta Vigo), Elliot Stroud (Mjallby), Daniel Svensson (Borussia Dortmund).

Midfielders: Taha Ali (Malmo), Yasin Ayari (Brighton), Lucas Bergvall (Tottenham), Jesper Karlstrom (Udinese), Ken Sema (Pafos), Mattias Svanberg (Wolfsburg), Besfort Zeneli (Union St-Gilloise).

Forwards: Alexander Bernhardsson (Holstein Kiel), Anthony Elanga (Newcastle), Viktor Gyokeres (Arsenal), Alexander Isak (Liverpool), Gustaf Nilsson (Club Brugge), Benjamin Nygren (Celtic).

### Tunisia

Goalkeepers: Sabri Ben Hessen (Etoile Sahel), Abdelmouhib Chamakh (Club Africain), Aymen Dahman (CS Sfaxien).

Defenders: Ali Abdi (Nice), Adem Arous (Kasimpasa), Mohamed Amine Ben Hamida (Esperance), Dylan Bronn (Servette), Raed Chikhaoui (US Monastir), Moutaz Neffati (Norrkoping), Omar Rekik (Maribor), Montassar Talbi (Lorient), Yan Valery (Young Boys).

Midfielders: Mortadha Ben Ouanes (Kasimpasa), Anis Ben Slimane (Norwich), Ismael Gharbi (Augsburg), Rani Khedira (Union Berlin), Mohamed Hadj Mahmoud (Lugano), Hannibal Mejbri (Burnley), Ellyes Skhiri (Eintracht Frankfurt).

Forwards: Elias Achouri (Copenhagen), Khalil Ayari (PSG), Firas Chaouat (Club Africain), Rayan Elloumi (Vancouver Whitecaps), Hazem Mastouri (Dynamo Makhachkala), Elias Saad (Hannover), Sebastian Tounekti (Celtic).

## Group G squads

### Belgium

Goalkeepers: Thibaut Courtois (Real Madrid), Senne Lammens (Man Utd), Mike Penders (Racing Strasbourg).

Defenders: Timothy Castagne (Fulham), Zeno Debast (Sporting Lisbon), Maxim De Cuyper (Brighton), Koni De Winter (AC Milan), Brandon Mechele (Club Brugge), Thomas Meunier (Lille), Nathan Ngoy (Lille), Joaquin Seys (Club Brugge), Arthur Theate (Eintracht Frankfurt).

Midfielders: Kevin De Bruyne (Napoli), Amadou Onana (Aston Villa), Nicolas Raskin (Rangers), Youri Tielemans (Aston Villa), Hans Vanaken (Club Brugge), Axel Witsel (Girona).

Forwards: Charles De Ketelaere (Atalanta), Jeremy Doku (Man City), Matias Fernandez-Pardo (Lille), Romelu Lukaku (Napoli), Dodi Lukebakio (Benfica), Diego Moreira (Strasbourg), Alexis Saelemaekers (AC Milan), Leandro Trossard (Arsenal).

### Egypt

Goalkeepers: Mohamed El Shenawy (Al Ahly), Mostafa Shobeir (Al Ahly), El Mahdi Soliman (Zamalek), Mohamed Alaa (El Gouna).

Defenders: Mohamed Hany (Al Ahly), Tarek Alaa (Zed), Hamdy Fathy (Al Wakrah), Rami Rabia (Al Ain), Yasser Ibrahim (Al Ahly), Hossam Abdelmaguid (Zamalek), Mohamed Abdelmonemn (Nice), Ahmed Fatouh (Zamalek), Karim Hafez (Pyramids).

Midfielders: Marwan Ateya (Al Ahly), Mohanad Lasheen (Pyramids), Nabil Emad (Al Najma), Mahmoud Saber (Zed), Ahmed Zizo (Al Ahly), Emam Ashour (Al Ahly), Mostafa Ziko (Pyramids), Mahmoud Trezeguet (Al Ahly), Ibrahim Adel (Nordsjaelland), Haissem Hassan (Real Ovideo).

Forwards: Omar Marmoush (Man City), Mohamed Salah (Liverpool), Aqtay Abdallah (Enppi), Hamza Abdelkarim (Barcelona).

### Iran

Goalkeepers: Alireza Beiranvand (Tractor FC), Seyed Hossein Hosseini (Sepahan), Payam Niazmand (Persepolis).

Defenders: Danial Eiri (Malavan), Ehsan Hajsafi (Sepahan), Saleh Hardani (Esteghlal), Hossein Kanaani (Persepolis), Shoja Khalilzadeh (Tractor FC), Milad Mohammadi (Persepolis), Ali Nemati (Foolad FC), Ramin Rezaeian (Foolad FC).

Midfielders: Rouzbeh Cheshmi (Esteghlal), Saeid Ezatolahi (Shabab Al Ahli), Mehdi Ghaedi (Al-Nasr), Saman Ghoddos (Kalba FC), Mohammad Ghorbani (Al-Wahda), Alireza Jahanbakhsh (FC Dender), Mohammad Mohebi (Rostov), Amir Mohammad Razzaghinia (Esteghlal), Mehdi Torabi (Tractor FC), Aria Yousefi (Sepahan).

Forwards: Ali Alipour (Persepolis), Dennis Dargahi (Standard Liege), Amirhossein Hosseinzadeh (Tractor FC), Mehdi Taremi (Olympiakos), Shahriar Moghanlou (Kalba FC).

### New Zealand

Goalkeepers: Max Crocombe (Millwall), Alex Paulsen (Lechia Gdansk), Michael Woud (Auckland).

Defenders: Tim Payne (Wellington Phoenix), Francis De Vries (Auckland), Tyler Bindon (Nottingham Forest), Michael Boxall (Minnesota Utd), Liberato Cacace (Wrexham), Nando Pijnaker (Auckland), Finn Surman (Portland Timbers), Callan Elliot (Auckland), Tommy Smith (Braintree Town).

Midfielders: Joe Bell (Viking FK), Matt Garbett (Peterborough), Marko Stamenic (Swansea), Sarpreet Singh (Wellington Phoenix), Alex Rufer (Wellington Phoenix), Ryan Thomas (PEC Zwolle).

Forwards: Chris Wood (Nottingham Forest), Eli Just (Motherwell), Kosta Barbarouses (Western Sydney Wanderers), Ben Waine (Port Vale), Ben Old (Saint-Etienne), Callum McCowatt (Silkeborg IF), Jesse Randall (Auckland), Lachlan Bayliss (Newcastle Jets).

## Group H squads

### Spain

Goalkeepers: Unai Simon (Athletic Club), David Raya (Arsenal), Joan Garcia (Barcelona).

Defenders: Aymeric Laporte (Athletic Club), Marc Cucurella (Chelsea), Marcos Llorente (Atletico Madrid), Eric Garcia (Barcelona), Pedro Porro (Tottenham), Alex Grimaldo (Bayer Leverkusen), Pau Cubarsi (Barcelona), Marc Pubill (Atletico Madrid).

Midfielders: Rodri (Manchester City), Fabian Ruiz (PSG), Mikel Merino (Arsenal), Pedri (Barcelona), Gavi (Barcelona), Martin Zubimendi (Arsenal), Alex Baena (Atletico Madrid).

Forwards: Ferran Torres (Barcelona), Mikel Oyarzabal (Real Sociedad), Dani Olmo (Barcelona), Nico Williams (Athletic Club), Lamine Yamal (Barcelona), Yeremy Pino (Crystal Palace), Borja Iglesias (Celta Vigo), Victor Munoz (Osasuna).

### Cape Verde

Goalkeepers: Vozinha (Chaves), Marcio Rosa (Montana), CJ dos Santos (San Diego).

Defenders: Stopira (Torreense), Roberto Lopes (Shamrock Rovers), Joao Paulo (FCSB), Diney (Al Bataeh), Logan Costa (Villarreal), Steven Moreira (Columbus Crew), Wagner Pina (Trabzonspor), Sidny Lopes Cabral (Benfica), Kelvin Pires (SJK).

Midfielders: Jamiro Monteiro (PEC Zwolle), Kevin Pina (Krasnodar), Deroy Duarte (Ludogorets), Telmo Arcanjo (Vitoria Guimaraes), Laros Duarte (Puskas Akademia), Yannick Semedo (Farense).

Forwards: Ryan Mendes (Igdir), Garry Rodrigues (Apollon Limassol), Willy Semedo (Omonia), Jovane Cabral (Estrela Amadora), Gilson Tavares (Akron Tolyatti), Dailon Livramento (Casa Pia), Helio Varela (Maccabi Tel Aviv), Nuno da Costa (Istanbul Basaksehir).

### Saudi Arabia

Goalkeepers: Mohammed Al Owais (Al Ula), Nawaf Al Aqidi (Al Nassr), Ahmed Al Kassar (Al Qadsiah).

Defenders: Abdulelah Al Amri (Al Nassr), Hassan Tambakti (Al Hilal), Jehad Thikri (Al Qadsiah), Ali Lajami (Al Hilal), Hassan Kadesh (Al Ittihad), Saud Abdulhamid (Lens, on loan from Roma), Mohammed Abu Al Shamat (Al Qadsiah), Ali Majrashi (Al Ahli), Moteb Al Harbi (Al Hilal), Nawaf Boushal (Al Nassr), Sultan Al-Ghannam (Al Nassr).

Midfielders: Mohammed Kanno (Al Hilal), Abdullah Al Khaibari (Al Nassr), Ziyad Al Johani (Al Ahli), Nasser Al Dawsari (Al Hilal), Musab Al Juwayr (Al Qadsiah), Alaa Al Hajji (Neom), Salem Al Dawsari (Al Hilal), Khalid Al Ghannam (Al Ettifaq), Ayman Yahya (Al Nassr).

Forwards: Firas Al Buraikan (Al Ahli), Saleh Al Shehri (Al Ittihad), Abdullah Al Hamdan (Al Nassr).

### Uruguay

Goalkeepers: Sergio Rochet (Internacional), Fernando Muslera (Estudiantes), Santiago Mele (Monterrey).

Defenders: Guillermo Varela (Flamengo), Ronald Araujo (Barcelona), Jose Maria Gimenez (Atletico Madrid), Santiago Bueno (Wolves), Sebastian Caceres (Club America), Mathias Olivera (Napoli), Joaquin Piquerez (Palmeiras), Matias Vina (Flamengo), Juan Manuel Sanabria (Real Salt Lake).

Midfielders: Manuel Ugarte (Manchester United), Emiliano Martinez (Palmeiras), Rodrigo Bentancur (Tottenham), Federico Valverde (Real Madrid), Agustin Canobbio (Fluminense), Giorgian de Arrascaeta (Flamengo), Nicolas de la Cruz (Flamengo), Facundo Pellistri (Panathinaikos), Rodrigo Zalazar (Braga), Maxi Araujo (Sporting), Brian Rodriguez (Club America).

Forwards: Rodrigo Aguirre (Club America), Federico Vinas (Real Oviedo), Darwin Nunez (Al Hilal).

## Group I squads

### France

Goalkeepers: Mike Maignan (AC Milan), Robin Risser (Lens), Brice Samba (Rennes).

Defenders: Lucas Digne (Aston Villa), Malo Gusto (Chelsea), Lucas Hernandez (PSG), Theo Hernandez (Al Hilal), Ibrahima Konate (Liverpool), Jules Kounde (Barcelona), Maxence Lacroix (Crystal Palace), William Saliba (Arsenal), Dayot Upamecano (Bayern Munich).

Midfielders: N'Golo Kante (Fenerbahce), Manu Kone (AS Roma), Adrien Rabiot (AC Milan), Aurelien Tchouameni (Real Madrid), Warren Zaire-Emery (PSG).

Forwards: Maghnes Akliouche (Monaco), Bradley Barcola (PSG), Rayan Cherki (Man City), Ousmane Dembele (PSG), Desire Doue (PSG), Jean-Philippe Mateta (Crystal Palace), Kylian Mbappe (Real Madrid), Michael Olise (Bayern Munich), Marcus Thuram (Inter Milan).

### Senegal

Goalkeepers: Edouard Mendy (Al Ahli), Mory Diaw (Le Havre AC), Yehvann Diouf (Nice).

Defenders: Krepin Diatta (Monaco), Antoine Mendy (Nice), Kalidou Koulibaly (Al-Hilal), El Hadji Malick Diouf (West Ham), Mamadou Sarr (Chelsea), Moussa Niakhate (Lyon), Moustapha Mbow (Paris FC), Abdoulaye Seck (Maccabi Haifa), Ismail Jakobs (Galatasaray), Ilay Camara (Anderlecht).

Midfielders: Idrissa Gana Gueye (Everton), Pape Gueye (Villarreal), Lamine Camara (Monaco), Habib Diarra (Sunderland), Pathe Ciss (Rayo Vallecano), Pape Matar Sarr (Tottenham), Bara Sapoko Ndiaye (Bayern Munich).

Forwards: Sadio Mane (Al Nassr), Ismaila Sarr (Crystal Palace), Iliman Ndiaye (Everton), Assane Diao (Como), Ibrahim Mbaye (PSG), Nicolas Jackson (Chelsea), Bamba Dieng (Lorient), Cherif Ndiaye (Samsunspor).

### Iraq

Goalkeepers: Fahad Talib (Al Talaba), Jalal Hassan (Al Zawraa), Ahmed Basil (Al Shorta).

Defenders: Hussein Ali (Pogon Szczecin), Manaf Younis, Ahmed Yahya, Mustafa Saadoon (Al Shorta), Zaid Tahseen (Pakhtakor), Rebin Sulaka (Port), Akam Hashim (Al Zawraa), Merchas Doski (Viktoria Plzen), Zaid Ismail (Al Talaba), Frans Putros (Persib).

Midfielders: Amir Al-Ammari (Cracovia), Kevin Yakob (Aarhus GF), Zidane Iqbal (Utrecht), Aimar Sher (Sarpsborg), Ibrahim Bayesh (Al Dhafra), Ahmed Qasem (Nashville SC), Youssef Amyn (AEK Larnaca), Marko Farji (Venezia).

Forwards: Ali Jassim (Al Najma), Ali Al-Hamadi (Ipswich), Ali Yousef (Al Talaba), Aymen Hussein (Al Karma), Mohanad Ali (Dibba).

### Norway

Goalkeepers: Orjan Haskjold Nyland (Sevilla), Egil Selvik (Watford), Sander Tangvik (Hamburger).

Defenders: Julian Ryerson (Borussia Dortmund), Marcus Holmgren Pedersen (Torino), David Moller Wolfe (Wolves), Fredrik Bjorkan (Bodo/Glimt), Kristoffer Ajer (Brentford), Torbjorn Heggem (Bologna), Leo Skiri Ostigard (Genoa), Sondre Langas (Derby), Henrik Falchener (Viking).

Midfielders: Martin Odegaard (Arsenal), Sander Berge (Fulham), Fredrik Aursnes (Benfica), Patrick Berg (Bodo/Glimt), Kristian Thorstvedt (Sassuolo), Morten Thorsby (Cremonese), Thelo Aasgaard (Rangers).

Forwards: Erling Haaland (Man City), Alexander Sorloth (Atletico Madrid), Jorgen Strand Larsen (Crystal Palace), Antonio Nusa (RB Leipzig), Oscar Bobb (Fulham), Andreas Schjelderup (Benfica), Jens Petter Hauge (Bodo/Glimt).

## Group J squads

### Argentina

Goalkeepers: Emiliano Martinez (Aston Villa), Juan Musso (Atletico Madrid), Geronimo Rulli (Marseille).

Defenders: Leonardo Balerdi (Marseille), Lisandro Martinez (Man Utd), Facundo Medina (Marseille), Nahuel Molina (Atletico Madrid), Gonzalo Montiel (River Plate), Nicolas Otamendi (Benfica), Cristian Romero (Tottenham), Nicolas Tagliafico (Lyon).

Midfielders: Valentin Barco (Strasbourg), Rodrigo De Paul (Inter Miami), Enzo Fernandez (Chelsea), Giovani Lo Celso (Real Betis), Alexis Mac Allister (Liverpool), Exequiel Palacios (Bayer Leverkusen), Leandro Paredes (Boca Juniors).

Forwards: Thiago Almada (Atletico Madrid), Julian Alvarez (Atletico Madrid), Nicolas Gonzalez (Atletico Madrid), Jose Manuel Lopez (Palmeiras), Lautaro Martinez (Inter Milan), Lionel Messi (Inter Miami), Nicolas Paz (Como), Giuliano Simeone (Atletico Madrid).

### Algeria

Goalkeepers: Luca Zidane (Granada), Oussama Benbot (USM Alger), Melvin Mastil (Stade Nyonnais).

Defenders: Aissa Mandi (Lille), Ramy Bensebaini (Borussia Dortmund), Mohamed Amine Tougai (Esperance de Tunis), Rayan Ait-Nouri (Man City), Jaouen Hadjam (Young Boys), Rafik Belghali (Hellas Verona), Zineddine Belaid (JS Kabylie), Achref Abada (USM Alger), Samir Chergui (Paris FC).

Midfielders: Nabil Bentaleb (Lille), Ramiz Zerrouki (Twente), Hicham Boudaoui (Nice), Fares Chaibi (Eintracht Frankfurt), Houssem Aouar (Al Ittihad), Ibrahim Maza (Bayer Leverkusen), Yacine Titraoui (Charleroi).

Forwards: Riyad Mahrez (Al Ahli), Mohamed Amoura (VfL Wolfsburg), Amine Gouiri (Marseille), Anis Hadj Moussa (Feyenoord), Adil Boulbina (Al Duhail), Nadhir Benbouali (Gyor), Fares Ghedjemis (Frosinone).

### Austria

Goalkeepers: Alexander Schlager (Red Bull Salzburg), Florian Wiegele (Viktoria Plzen), Patrick Pentz (Brondby).

Defenders: David Affengruber (Elche), Kevin Danso (Tottenham), Stefan Posch (Como), David Alaba (Real Madrid), Philipp Lienhart (Freiburg), Phillipp Mwene (Mainz), Alexander Prass (Hoffenheim), Marco Friedl (Werder Bremen), Michael Svoboda (Venezia).

Midfielders: Xaver Schlager (RB Leipzig), Nicolas Seiwald (RB Leipzig), Marcel Sabitzer (Borussia Dortmund), Florian Grillitsch (Braga), Carney Chukwuemeka (Borussia Dortmund), Romano Schmid (Werder Bremen), Christoph Baumgartner (Hoffenheim), Konrad Laimer (Bayern Munich), Patrick Wimmer (VfL Wolfsburg), Paul Wanner (PSV), Alessandro Schopf (Wolfsberger).

Forwards: Marko Arnautovic (Red Star Belgrade), Michael Gregoritsch (Brondby), Sasa Kalajdzic (Stuttgart).

### Jordan

Goalkeepers: Yazeed Abulaila (Al Hussein), Abdallah Al-Fakhouri (Al Wehdat), Nour Bani Attiah (Al Faisaly).

Defenders: Ihsan Haddad (Al Hussein), Yazan Al-Arab (FC Seoul), Abdallah Nasib (Al Zawraa), Mohammad Abu Hashish (Al Karma), Saed Al-Rosan (Al Hussein), Husam Abu Dahab (Al Faisaly), Mo Abualnadi (Selangor), Salim Obaid (Al Hussein), Anas Badawi (Al Faisaly).

Midfielders: Rajaei Ayed (Al Hussein), Noor Al-Rawabdeh (Selangor), Ibrahim Sadeh (Al-Karma), Nizar Al-Rashdan (Qatar SC), Mohannad Abu Taha (Al Quwa Al Jawiya), Amer Jamous (Al Zawraa), Mohammad Al-Dawoud (Al Wehdat).

Forwards: Musa Al-Taamari (Rennes), Mahmoud Al-Mardi (Al Hussein), Ali Olwan (Al Sailiya), Mohammad Abu Zrayq (Raja Casablanca), Odeh Al-Fakhouri (Pyramids), Ibrahim Sabra (Lokomotiva Zagreb), Ali Azaizeh (Al Shabab).

## Group K squads

### Portugal

Goalkeepers: Diogo Costa (Porto), Jose Sa (Wolves), Rui Silva (Sporting), Ricardo Velho (Genclerbirligi).

Defenders: Diogo Dalot (Man Utd), Matheus Nunes (Man City), Nelson Semedo (Fenerbahce SK), Joao Cancelo (Barcelona), Nuno Mendes (PSG), Goncalo Inacio (Sporting), Renato Veiga (Villarreal), Ruben Dias (Man City), Tomas Araujo (Benfica).

Midfielders: Ruben Neves (Al Hilal), Samuel Costa (Mallorca), Joao Neves (PSG), Vitinha (PSG), Bruno Fernandes (Man Utd), Bernardo Silva (Man City).

Forwards: Joao Felix (Al Nassr), Francisco Trincao (Sporting), Francisco Conceicao (Juventus), Pedro Neto (Chelsea), Rafael Leao (AC Milan), Goncalo Guedes (Real Sociedad), Goncalo Ramos (PSG), Cristiano Ronaldo (Al Nassr).

### DR Congo

Goalkeepers: Matthieu Epolo (Standard Liege), Timothy Fayulu (Noah), Lionel Mpasi (Le Havre).

Defenders: Dylan Batubinsika (Larisa), Rocky Bushiri (Hibernian), Gedeon Kalulu (Aris Limassol), Steve Kapuadi (Widzew Lodz), Joris Kayembe (Racing Genk), Arthur Masuaku (Racing Lens), Chancel Mbemba (Lille), Axel Tuanzebe (Burnley), Aaron Wan-Bissaka (West Ham).

Midfielders: Theo Bongonda (Spartak Moscow), Brian Cipenga (Castellon), Meshack Elia (Alanyaspor), Gael Kakuta (Larisa), Edo Kayembe (Watford), Nathanael Mbuku (Montpellier), Samuel Moutoussamy (Atromitos), Ngal'ayel Mukau (Lille), Charles Pickel (Espanyol), Noah Sadiki (Sunderland).

Forwards: Cedric Bakambu (Real Betis), Simon Banza (Al Jazira), Fiston Mayele (Pyramids), Yoane Wissa (Newcastle).

### Uzbekistan

Goalkeepers: Utkir Yusupov (Navbahor), Abduvohid Nematov (Nasaf), Botirali Ergashev (Neftchi).

Defenders: Rustam Ashurmatov (Esteghlal), Farrukh Sayfiev (Neftchi), Khojiakbar Alijonov (Pakhtakor), Sherzod Nasrullaev (Nasaf), Umar Eshmurodov (Nasaf), Abdukodir Khusanov (Man City), Abdulla Abdullaev (Dibba), Bekhruz Karimov (Surkhon), Jakhongir Urozov (Dinamo Samarqand), Avazbek Ulmasaliev (AGMK).

Midfielders: Otabek Shukurov (Baniyas), Jaloliddin Masharipov (Esteghlal), Odiljon Hamrobekov (Tractor), Oston Urunov (Persepolis), Jamshid Iskanderov (Neftchi), Dostonbek Khamdamov (Pakhtakor), Abbosbek Fayzullaev (Istanbul Basaksehir), Akmal Mozgovoy (Pakhtakor), Azizjon Ganiev (Al Bataeh), Sherzod Esanov (Bukhara).

Forwards: Eldor Shomurodov (Istanbul Basaksehir), Igor Sergeev (Persepolis), Azizbek Amonov (Bukhara).

### Colombia

Goalkeepers: Camilo Vargas (Atlas), Alvaro Montero (Velez Sarsfield), David Ospina (Atletico Nacional).

Defenders: Davinson Sanchez (Galatasaray), Jhon Lucumi (Bologna), Yerry Mina (Cagliari), Willer Ditta (Cruz Azul), Daniel Munoz (Crystal Palace), Santiago Arias (Independiente), Johan Mojica (Mallorca), Deiver Machado (Nantes).

Midfielders: Richard Rios (Benfica), Jefferson Lerma (Crystal Palace), Kevin Castano (River Plate), Juan Camilo Portilla (Athletico Paranaense), Gustavo Puerta (Racing de Santander), Jhon Arias (Palmeiras), Jorge Carrascal (Flamengo), Juan Fernando Quintero (River Plate), James Rodriguez (Minnesota Utd), Jaminton Campaz (Rosario Central).

Forwards: Juan Camilo Hernandez (Real Betis), Luis Diaz (Bayern Munich), Luis Suarez (Sporting), Carlos Andres Gomez (Vasco da Gama), Jhon Cordoba (FC Krasnodar).

## Group L squads

### England

Goalkeepers: Jordan Pickford (Everton), Dean Henderson (Crystal Palace), James Trafford (Man City).

Defenders: Reece James (Chelsea), Ezri Konsa (Aston Villa), Jarell Quansah (Bayer Leverkusen), John Stones (Man City), Marc Guehi (Man City), Dan Burn (Newcastle), Nico O'Reilly (Man City), Djed Spence (Tottenham), Tino Livramento (Newcastle).

Midfielders: Declan Rice (Arsenal), Elliot Anderson (Nottingham Forest), Kobbie Mainoo (Man Utd), Jordan Henderson (Brentford), Morgan Rogers (Aston Villa), Jude Bellingham (Real Madrid), Eberechi Eze (Arsenal).

Forwards: Harry Kane (Bayern Munich), Ivan Toney (Al Ahli), Ollie Watkins (Aston Villa), Bukayo Saka (Arsenal), Marcus Rashford (Barcelona), Anthony Gordon (Newcastle), Noni Madueke (Arsenal).

### Croatia

Goalkeepers: Dominik Livakovic (Dinamo Zagreb), Dominik Kotarski (Copenhagen), Ivor Pandur (Hull).

Defenders: Josko Gvardiol (Man City), Duje Caleta-Car (Real Sociedad), Josip Sutalo (Ajax), Josip Stanisic (Bayern Munich), Marin Pongracic (Fiorentina), Martin Erlic (Midtjylland), Luka Vuskovic (Hamburg).

Midfielders: Luka Modric (AC Milan), Mateo Kovacic (Man City), Mario Pasalic (Atalanta), Nikola Vlasic (Torino), Luka Sucic (Real Sociedad), Martin Baturina (Como), Kristijan Jakic (Augsburg), Petar Sucic (Inter Milan), Nikola Moro (Bologna), Toni Fruk (Rijeka).

Forwards: Ivan Perisic (PSV Eindhoven), Andrej Kramaric (Hoffenheim), Ante Budimir (Osasuna), Marco Pasalic (Orlando City), Petar Musa (Dallas), Igor Matanovic (Freiburg).

### Ghana

Goalkeepers: Benjamin Asare (Accra Hearts of Oak SC), Lawrence Ati-Zigi (St Gallen), Joseph Anang (St Patrick's Athletic).

Defenders: Baba Abdul Rahman (PAOK), Gideon Mensah (Auxerre), Marvin Senaya (Auxerre), Alidu Seidu (Rennes), Abdul Mumin (Rayo Vallecano), Jerome Opoku (Istanbul Basaksehir), Jonas Adjetey (Wolfsburg), Kojo Oppong Peprah (Nice), Elisha Owusu (Auxerre), Derrick Luckassen (Pafos).

Midfielders: Thomas Partey (Villarreal), Kwasi Sibo (Real Oviedo), Augustine Boakye (Saint-Etienne), Caleb Yirenkyi (Nordsjaelland), Abdul Fatawu Issahaku (Leicester).

Forwards: Kamaldeen Sulemana (Atalanta), Christopher Bonsu Baah (Al Qadsiah), Ernest Nuamah (Lyon), Antoine Semenyo (Man City), Brandon Thomas-Asante (Coventry), Prince Kwabena Adu (Viktoria Plzen), Inaki Williams (Athletic Club), Jordan Ayew (Leicester).

### Panama

Goalkeepers: Luis Mejia (Nacional), Orlando Mosquera (Al Fayha), Cesar Samudio (Marathon).

Defenders: Eric Davis (Plaza Amador), Fidel Escobar (Saprissa), Michael Amir Murillo (Besiktas), Roderick Miller (Turan Tovuz), Andres Andrade (LASK), Cesar Blackman (Slovan Bratislava), Jose Cordoba (Norwich), Jiovany Ramos (Puerto Cabello), Jorge Gutierrez (Deportivo La Guaira), Edgardo Farina (Pari Nizhny Novgorod).

Midfielders: Anibal Godoy (San Diego), Alberto Quintero (Plaza Amador), Yoel Barcenas (Mazatlan), Adalberto Carrasquilla (UNAM), Jose Luis Rodriguez (Juarez), Cristian Martinez (Ironi Kiryat Shmona), Cesar Yanis (Cobresal), Carlos Harvey (Minnesota Utd), Azarias Londono (Universidad Catolica).

Forwards: Jose Fajardo (Universidad Catolica), Ismael Diaz (Leon), Cecilio Waterman (Universidad de Concepcion), Tomas Rodriguez (Saprissa).
"""


def strip_accents(s):
    """Remove accents from string for fuzzy matching."""
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def normalize_name(name):
    """Normalize player name for matching."""
    name = name.strip()
    # Handle special cases
    # Remove (on loan from X) suffixes
    name = re.sub(r'\s*\([^)]*loan[^)]*\)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\([^)]*\)', '', name)  # Remove parentheticals
    # Accented names: Sane <-> Sané, Nubel <-> Nübel
    name = strip_accents(name)
    name = name.lower().strip()
    return name


def parse_squads(text):
    """Parse Sky Sports squad text into dict: team_name -> [player_names]"""
    squads = {}
    
    # Split by team headers (### Team Name)
    # First get all sections between ### headers
    teams_pattern = re.compile(r'###\s+(.+?)\n(.*?)(?=\n###|\Z)', re.DOTALL)
    
    for match in teams_pattern.finditer(text):
        team_name = match.group(1).strip()
        team_text = match.group(2).strip()
        
        players = {}
        # Extract player names from Goalkeepers:/Defenders:/Midfielders:/Forwards: sections
        section_pattern = re.compile(r'(?:Goalkeepers|Defenders|Midfielders|Forwards):(.*?)(?=\n\n|\Z|(?:Goalkeepers|Defenders|Midfielders|Forwards):)', re.DOTALL)
        
        for section_match in section_pattern.finditer(team_text):
            section_content = section_match.group(1)
            # Extract individual player names (before the parenthetical club)
            # Pattern: Name (Club) or just Name
            # Handle both comma and semicolon separators
            player_pattern = re.compile(r'([^,;]+?)\s*\([^)]*\)')
            for p_match in player_pattern.finditer(section_content):
                player_name = p_match.group(1).strip()
                if player_name and player_name not in ['Also See:']:
                    players[normalize_name(player_name)] = player_name
        
        if players:
            squads[team_name] = players
    
    return squads


def slug_to_team_name():
    """Map FBref slug to team name used in Sky Sports."""
    mapping = {
        # Match FBref slug -> Sky Sports team name
        "algeria": "Algeria",
        "argentina": "Argentina",
        "australia": "Australia",
        "austria": "Austria",
        "belgium": "Belgium",
        "bosnia-and-herzegovina": "Bosnia-Herzegovina",
        "brazil": "Brazil",
        "canada": "Canada",
        "cape-verde": "Cape Verde",
        "colombia": "Colombia",
        "congo-dr": "DR Congo",
        "cote-divoire": "Ivory Coast",
        "croatia": "Croatia",
        "curacao": "Curacao",
        "czechia": "Czech Republic",
        "ecuador": "Ecuador",
        "egypt": "Egypt",
        "england": "England",
        "france": "France",
        "germany": "Germany",
        "ghana": "Ghana",
        "haiti": "Haiti",
        "ir-iran": "Iran",
        "iraq": "Iraq",
        "japan": "Japan",
        "jordan": "Jordan",
        "korea-republic": "South Korea",
        "mexico": "Mexico",
        "morocco": "Morocco",
        "netherlands": "Netherlands",
        "new-zealand": "New Zealand",
        "norway": "Norway",
        "panama": "Panama",
        "paraguay": "Paraguay",
        "portugal": "Portugal",
        "qatar": "Qatar",
        "saudi-arabia": "Saudi Arabia",
        "scotland": "Scotland",
        "senegal": "Senegal",
        "south-africa": "South Africa",
        "spain": "Spain",
        "sweden": "Sweden",
        "switzerland": "Switzerland",
        "tunisia": "Tunisia",
        "turkiye": "Turkey",
        "united-states": "USA",
        "uruguay": "Uruguay",
        "uzbekistan": "Uzbekistan",
    }
    return mapping


def main():
    # Parse squads
    print("Parsing Sky Sports squad data...")
    squads = parse_squads(SKY_SPORTS_TEXT)
    print(f"  Found {len(squads)} teams")
    
    # Load WCQ data
    wcq_path = os.path.join(DATA_DIR, "wcq_player_stats.json")
    print(f"\nLoading WCQ data from {wcq_path}...")
    with open(wcq_path, 'r', encoding='utf-8') as f:
        wcq_data = json.load(f)
    print(f"  {len(wcq_data)} teams in WCQ data")
    
    # Build slug -> team name mapping
    slug_map = slug_to_team_name()
    
    # Filter: For each team, only keep players in the 26-man squad
    filtered_data = {}
    total_wcq = 0
    total_in_squad = 0
    
    for team_slug, players in wcq_data.items():
        total_wcq += len(players)
        team_name = slug_map.get(team_slug.lower(), team_slug.replace('-', ' ').title())
        
        squad_players = squads.get(team_name, {})
        
        if not squad_players:
            print(f"  ⚠ No squad data for '{team_name}' (slug: {team_slug}), keeping all {len(players)} players")
            filtered_data[team_slug] = players
            total_in_squad += len(players)
            continue
        
        matches = []
        for p in players:
            pname = p.get('player', '')
            pnorm = normalize_name(pname)
            
            if pnorm in squad_players:
                matches.append(p)
                continue
            
            # Try fuzzy match strategies
            found = False
            for snorm, sname in squad_players.items():
                # Strategy 1: Check if one contains the other
                if pnorm in snorm or snorm in pnorm:
                    if abs(len(pnorm) - len(snorm)) <= 3:
                        matches.append(p)
                        found = True
                        break
                
                # Strategy 2: Reversed name order (Korean: "Hwang In-beom" vs "In-Beom Hwang")
                p_parts = pnorm.split()
                if len(p_parts) >= 2:
                    p_reversed = ' '.join(reversed(p_parts))
                    if p_reversed == snorm:
                        matches.append(p)
                        found = True
                        break
                    # Also try reversed with contains check
                    if p_reversed in snorm or snorm in p_reversed:
                        matches.append(p)
                        found = True
                        break
                
                # Strategy 3: Sky uses only last name (Australia: "Ryan" for "Mathew Ryan")
                if ' ' not in snorm and ' ' in pnorm:
                    p_last = pnorm.split()[-1]
                    if p_last == snorm:
                        matches.append(p)
                        found = True
                        break
                
                # Strategy 4: Both names with hyphen - check parts
                p_parts_hyphen = pnorm.replace('-', ' ').split()
                s_parts_hyphen = snorm.replace('-', ' ').split()
                if len(p_parts_hyphen) == 2 and len(s_parts_hyphen) == 2:
                    if set(p_parts_hyphen) == set(s_parts_hyphen):
                        matches.append(p)
                        found = True
                        break
            
            if not found:
                pass  # Player not in squad
        
        total_in_squad += len(matches)
        filtered_data[team_slug] = matches
        
        if len(matches) < len(players):
            pass  # Some filtered out
        
        # Print summary for a few teams
        if team_slug in ['germany', 'spain', 'canada']:
            squad_names = set(squad_players.values())
            matched_names = [p['player'] for p in matches]
            print(f"\n  {team_name}: {len(matches)}/{len(players)} in squad")
            for p in players:
                in_squad = "✓" if p['player'] in matched_names else "✗"
                print(f"    {in_squad} {p['player']}")
    
    print(f"\n\nSummary: {total_wcq} total players -> {total_in_squad} in World Cup squads ({total_wcq - total_in_squad} removed)")
    
    # Save filtered data
    filtered_path = os.path.join(DATA_DIR, "wcq_player_stats_filtered.json")
    with open(filtered_path, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=2)
    print(f"Filtered data saved to {filtered_path}")
    
    # Also save the squad mapping for reference
    squad_path = os.path.join(DATA_DIR, "wc_squads.json")
    json_squads = {team: list(players.values()) for team, players in squads.items()}
    with open(squad_path, 'w', encoding='utf-8') as f:
        json.dump(json_squads, f, ensure_ascii=False, indent=2)
    print(f"Squad data saved to {squad_path}")
    
    return filtered_data


if __name__ == "__main__":
    main()
