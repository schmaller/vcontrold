# vcontrold

_vcontrold_ is a software daemon written in C for communication with the "Optolink" interface of Viessmann Vito heating controllers.

For building and installation instructions see `doc/INSTALL.md`.

[Binary packages](https://github.com/openv/vcontrold/releases) are available for different platforms.

Please visit the [OpenV Wiki](https://github.com/openv/openv/wiki/) for in-depth info and examples.

## DE

_vcontrold_ ist ein in C geschriebener Software-Daemon zur Kommunikation mit der „Optolink“-Schnittstelle von Viessmann-Vito-Heizungssteuerungen.

Der Build-Prozess und die Installation sind kurz unter `doc/INSTALL.md` beschrieben.

Für einige Plattformen sind kompilierte [Installations-Pakete](https://github.com/openv/vcontrold/releases) verfügbar.

Infos zur Einrichtung und Benutzung sind im [OpenV-Wiki](https://github.com/openv/openv/wiki/) beschrieben.

## :moneybag: Skript vito_watcher.py
Die [hier gestellte Frage](https://github.com/openv/openv/issues/307) ist zwar schon 5 Jahre alt, aber das Thema dank Gasknappheit wieder brandaktuell:

**Heizungsunterstützung der Gasbrennwerttherme durch solarthermisch beheizten Warmwassertank**

Seitdem meine Kollektoren bereits im April und bis in den Oktober hinein den Wasserspeicher viel mehr erwärmen, als wir es benötigen,
fragte ich mich, ob man die überschüssige Wärme nicht für die Fussbodenheizung nutzen kann.
Ja, ich weiss, es gibt Lösungen, bei denen die Vitosol und die Vitodens verbunden sind, und da klappt das Zusammenspiel wahrscheinlich "out of the box".
Bei uns sind Therme und Solarkollektoren aber nur über den Wassertank verbunden. Die Gastherme heizt den Wassertank auf, wenn die solare Wärmelieferung dazu nicht ausreicht.

Die Idee war nun, dazu die Befüllungsfunktion der Vitodens 300W zu nutzen,
welche das Umschaltventil in Mittelstellung bringt und die Zirkulationspumpe einschaltet.
Dadurch wird das warme Wasser aus dem Heizkreislauf des WW-Speichers in den Heizkessel der Gastherme befördert
und kann anschließend von dort über den Mischer der FBH zugeführt werden.

Zur Steuerung des ganzen habe ich ein [kleines Python-Skript](https://github.com/schmaller/vcontrold/tree/master/tools/vito_watcher) geschrieben,
welches auf einem Raspberry Pi Zero läuft, der mit einem USB-OptoLink-Adapter an der Vitodens angeschlossen ist.
Dieses fragt die relevanten Temparatur- und Statuswerte der Heitung ab und entscheidet, wann und für wie lange die Befüllungsfunktion eingeschaltet wird.
Darüberhinaus werden in regelmäßigen Zeitintervallen die ermittelten Werte in eine rudimäntäre JSON-DB geschrieben.

Vorraussetzung für die Lauffähigkeit des Skriptes ist ein funktionierender vcontrold und die Erweiterungen in der vito.xml und vcontrol.xml für die Befüllungsfunktion.
https://github.com/schmaller/vcontrold/tree/master/xml/300

Fragen, Anregungen und Kommentare gerne über das Github-Repo: https://github.com/schmaller/vcontrold
