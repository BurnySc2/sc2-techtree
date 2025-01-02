from generate.collect import collect
from generate.patch import patch

"""
To be able to run this, you need to have the "Empty128" map downloaded and in your SC2/maps folder.
You can download the map from here ("Melee" link):
https://github.com/Blizzard/s2client-proto#map-packs

Direct link: 
http://blzdistsc2-a.akamaihd.net/MapPacks/Melee.zip
"""


def main():
    collect()
    patch()


if __name__ == "__main__":
    main()
