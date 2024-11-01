# Inspect Image

II.py checks images (or folders) for naming or structural problems. 

The goal is to ensure a uniform structure and naming. A possible use case is the creation of data mediums (such as DVDs), for which one would like to ensure a uniform structure.

The desired structure and rules are defined once in an xml file. The program reads the rules and applies them to a given directory. As a result, II.py lists all deviations that do not correspond to the specifications in the xml file.

## Install

1. Install Python3 as follows in Ubuntu/Debian Linux:
```
sudo apt install python3.6
```

2. Download II.py and set execute permmissions:
```
curl -LJO https://raw.githubusercontent.com/byte-cook/inspect-image/main/ii.py
curl -LJO https://raw.githubusercontent.com/byte-cook/inspect-image/main/xmlutil.py
chmod +x ii.py 
```

3. (Optional) Use opt.py to install it to the /opt directory:
```
sudo opt.py install inspect-image ii.py xmlutil.py
```

## Define desired structure and rules

See ii.xml for an example of how to define the rules.

## Example usage

Check the current directory if all defined rules of profile "mp3" are fulfilled:
```
ii.py mp3 
```

