import zstandard as zstd


def stream_decompress(input_path: str, read_size: int = 65536):
    dctx = zstd.ZstdDecompressor()
    with open(input_path, "rb") as file_handle:
        yield from dctx.read_to_iter(file_handle, read_size=read_size)
