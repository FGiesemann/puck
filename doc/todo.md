# TODO List for Puck

## CMake Optionen in lokaler Build-Konfiguration

### Ziel

Der Benutzer kann CMake-Optionen bzw. -Variablen in der lokalen
Build-Konfiguration angeben, z. B. damit CMake externe Abhängigkeiten finden
kann (bspw. `CMAKE_PREFIX_PATH`)
  
### Erweiterung: Vordefinierte "Bibliotheken"

Die globale puck-Konfiguration könnte Bibliotheken vordefinieren (z. B. Qt6),
die solche Variablen/Settings mitbringen, und die dann lokal in der
Build-Konfiguration nur noch referenziert werden müssen.

### Hinweise

Die Konfiguration muss Projektweise möglich sein, da nicht alle Konfigurationen
oder Libraries von allen Projekten genutzt werden sollen.

### Implementierungsansatz

Lokale Build-Konfiguration erweitern um `project_settings`-Block. Darin für
einzelne Projekte `cmake_settings` und ggf. auch `conan_settings` bzw. `imports`
für vordefnierte Bibliotheken.

```json
// puck-build.json
{
    "profiles": [
        "..."
    ],

    "project_settings": {
      "Project_A": {
        "imports": ["Qt6", "Sqlite3"],
          "cmake_vars": {
            "CUSTOM_BUILD_FLAG": "TRUE"
          },
          "conan_env_vars": {
            "CUSTOM_GENERATOR_PATH": "/opt/custom_tool/bin",
            "LICENSE_KEY": "XYZ-123"
          }
        }
    }
}
```

```json
// global .puck/libraries.json
{
    "libraries": [
        {
            "name": "Qt6",
            "cmake_vars": {
                "QT6_DIR": "/opt/Qt/6.6.0"
            }
        },
        {
            "name": "Sqlite3",
            "cmake_vars": {
                ...
            }
        }
    ]
}
```

## Mehr Kommandos

### Ziel

Puck sollte noch weitere Kommandos oder Erweiterungen von Kommandos anbieten,
die über alle Projekte ausgeführt werden sollen.

### Mögliche Kommandos

- `pull` -> Aktualisiere alle aktuell ausgecheckten branches
- `clean` -> Lösche alle build-Artefakte, CMake Cache
- `install --update` -> Aktualisiere die conan-Abhängigkeiten
- `test` -> Alle Tests ausführen

## Bessere Fehlermeldungen

### Ziel

Fehlermeldungen sollten klar erkennbar auf den Fehler hinweisen.
Exception-Handling von Python sollte nicht zu sehen sein.

## Generierung von Projektdateien für IDEs

### Ziel

Puck könnte Projektdateien für IDEs generieren, damit Projekte leichter
importiert werden können.

### Implementierungsansatz

Nutze CMake-Generatoren, um die Projektdateien zu generieren
(via `cmake -G <generator>`)

## Pacakge Lifecycle

### Ziel

Puck kann conan Packages erstellen und ggf. hochladen.

### Implementierungsansatz

Nutze `conan create` und weitere relevante Kommandos.

## MSVC-Umgebungsinitialisierung

### Ziel

Automatische Initialisierung der Microsoft Visual C++ (MSVC) Umgebung für cmake
und conan Aufrufe unter Windows, sodass Benutzer puck aus jeder Standard-Shell
(CMD, PowerShell) ausführen können, ohne manuell die Developer Command Prompt
starten zu müssen.

### Implementierungsansatz

Microsoft stellt ein Tool/API bereit, um die installierten Visual Studio
Versionen, bzw. Build-Tools abzurufen: Visual Studio Build Tools Installer und
Querier bzw. Visual Studio Setup API.

1. Plattform-Erkennung: In der puck.py oder der Workspace-Klasse prüfen, ob das
  aktuelle Betriebssystem Windows ist (os.name == 'nt').
1. Compiler-Erkennung: Prüfen, ob das aktuell verwendete Conan-Profil einen
  MSVC-Compiler (z.B. msvc) konfiguriert hat.
1. Setup-API-Abfrage

    - Implementierung: Implementieren Sie eine neue VSToolFinder-Klasse (z.B. in
      C#/.NET, PowerShell, oder nutzen Sie die Python-Schnittstellen, falls
      vorhanden), die das Visual Studio Setup API abfragt.
    - Ergebnis: Dieses Tool liefert den zuverlässigen, absoluten Pfad zur
      benötigten VS-Installation basierend auf der Compilerversion (z.B.
      msvc.version=193).

1. Umgebungsextraktion und Injektion
    - Ausführung: Führen Sie `vcvarsall.bat <arch>` in einem separaten Prozess
      aus und fangen Sie die resultierenden Umgebungsvariablen (insbesondere
      PATH, INCLUDE, LIB) ab, die das Skript setzt.
    - Injektion: Fügen Sie diese extrahierten Variablen in die env-Map des
      nachfolgenden subprocess.run-Aufrufs für cmake configure ein.
