from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser, QVBoxLayout, QWidget


class UserGuideDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Guide rapide")
        self.resize(820, 680)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(_GUIDE_HTML)
        browser.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(browser, stretch=1)
        layout.addWidget(buttons)


_GUIDE_HTML = """
<h1>Open Fish Reader</h1>
<p><b>Dépouillement vidéo et saisie des passages piscicoles</b></p>

<h2>1. Ouvrir une station</h2>
<ol>
  <li>Cliquez sur <b>Ouvrir une station</b>.</li>
  <li>Sélectionnez le dossier racine de la station.</li>
  <li>Choisissez ensuite une journée avec <b>Choisir la journée</b>.</li>
</ol>

<h2>2. Naviguer dans les vidéos</h2>
<ul>
  <li>Utilisez les boutons du bandeau inférieur ou les flèches du clavier.</li>
  <li><b>Espace</b> lance ou met en pause la lecture.</li>
  <li>Les informations de station, journée, fichier, image et horodatage sont affichées au-dessus de la vidéo.</li>
</ul>

<h2>3. Enregistrer un passage</h2>
<ol>
  <li>Sélectionnez un taxon dans le panneau <b>Observation rapide</b>.</li>
  <li>Renseignez le nombre, la position vitre, la confiance et le commentaire si nécessaire.</li>
  <li>Validez avec <b>−1</b> pour une dévalaison, <b>0</b> pour un sens indéterminé ou <b>+1</b> pour une montaison.</li>
</ol>
<p>Le taxon reste sélectionné après l'enregistrement. Les autres champs reviennent à leurs valeurs par défaut.</p>

<h2>4. Mesurer un poisson</h2>
<ol>
  <li>Vérifiez qu'une calibration est valide dans <b>Configuration &gt; Relations taille / pixels</b>.</li>
  <li>Choisissez la position vitre : proche, milieu ou loin.</li>
  <li>Cliquez sur <b>Mesurer…</b>.</li>
  <li>Placez de 2 à 100 points le long de l'axe du poisson.</li>
  <li>Terminez avec <b>Entrée</b> ou un double-clic.</li>
  <li>Validez ensuite le passage avec −1, 0 ou +1.</li>
</ol>
<p><b>Ctrl+Z</b> ou Retour arrière retire le dernier point. <b>Échap</b> annule la mesure.</p>

<h2>5. Consulter les passages</h2>
<ul>
  <li>Ouvrez <b>Passages</b> dans la barre principale.</li>
  <li>Filtrez par date et heure.</li>
  <li>Double-cliquez pour modifier un passage.</li>
  <li>Utilisez <b>Afficher dans le lecteur</b> pour revenir à son image.</li>
  <li>Ctrl+clic ou Maj+clic permet une suppression multiple.</li>
  <li>L'export CSV reprend la période affichée.</li>
</ul>

<h2>6. Exporter des médias</h2>
<p>Le bouton <b>Exporter…</b> du lecteur permet d'exporter l'image affichée, la séquence vidéo complète, ou les deux. Le dossier racine est mémorisé et les fichiers peuvent être rangés automatiquement par taxon.</p>

<h2>7. Sauvegarder la base</h2>
<p>Cliquez sur <b>Sauvegarder la base…</b>. La copie est réalisée avec l'API de sauvegarde SQLite puis vérifiée avec <code>PRAGMA integrity_check</code> et <code>PRAGMA foreign_key_check</code>.</p>

<h2>8. En cas de problème</h2>
<p>Ouvrez <b>Aide &gt; Ouvrir le dossier des journaux</b>. Le fichier <code>open-fish-reader.log</code> contient les informations de diagnostic.</p>
"""
