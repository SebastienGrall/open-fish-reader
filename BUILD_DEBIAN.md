# Construire le paquet Debian

Construction obligatoire sous Debian avec le venv du projet actif.

```bash
sudo apt update
sudo apt install -y build-essential dpkg-dev fakeroot \
  libgl1 libegl1 libxkbcommon0 libxkbcommon-x11-0 libxcb-cursor0

python -m pip install -e '.[dev]'
./build_deb.sh
```

Résultat :

```text
deb_dist/open-fish-reader_X.Y.Z_amd64.deb
```

Installation et désinstallation :

```bash
sudo apt install ./deb_dist/open-fish-reader_X.Y.Z_amd64.deb
sudo apt remove open-fish-reader
```

Les données utilisateur restent dans le dossier local géré par platformdirs et ne sont pas supprimées par `apt remove`.

Le paquet doit être reconstruit séparément sur chaque architecture (`amd64`, `arm64`). Un paquet PyInstaller Linux ne peut pas être produit depuis Windows.
