class OpenFishReaderError(Exception):
    pass


class InvalidStationFolderError(OpenFishReaderError):
    pass


class InvalidVideoPartJsonError(OpenFishReaderError):
    pass


class UnsupportedJsonSchemaError(OpenFishReaderError):
    pass
