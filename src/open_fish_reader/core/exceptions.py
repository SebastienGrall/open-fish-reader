class OpenFishReaderError(Exception):
    """Erreur de base du logiciel."""


class InvalidStationFolderError(OpenFishReaderError):
    pass


class InvalidVideoPartJsonError(OpenFishReaderError):
    pass


class UnsupportedJsonSchemaError(OpenFishReaderError):
    pass


class IgnoredJsonRecordError(OpenFishReaderError):
    """Le JSON est valide, mais ne décrit pas une partie vidéo."""
