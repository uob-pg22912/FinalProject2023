import asyncio
import os

from tqdm import tqdm

_ANALYSIS_TOOLS_JAR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs", "analysis_tools.jar")


async def run_analysis_tools(output_dir: str, apk_paths: list[str]) -> dict[str, tuple[bool, str]]:
    apk_path_args = " ".join([f"\"{i}\"" for i in apk_paths])
    process = await asyncio.create_subprocess_shell(
        f"java -jar \"{_ANALYSIS_TOOLS_JAR_PATH}\" --output \"{output_dir}\" {apk_path_args}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )
    process_start = False
    result: dict[str, tuple[bool, str]] = {}
    with tqdm(total=len(apk_paths)) as pbar:
        while True:
            line = await process.stdout.readline()
            if line == b'':
                break
            elif line:
                line_str = line.decode().strip()
                if process_start:
                    if line_str.startswith("Success"):
                        pbar.update(1)
                        input_path, output_path = [i.strip().strip("\'") for i in line_str.split(":")[1].split("->")]
                        result[input_path] = (True, output_path)
                    elif line_str.startswith("Error"):
                        pbar.update(1)
                        input_path, error = [i.strip().strip("\'") for i in line_str.split(":")[1].split("->")]
                        result[input_path] = (True, error)
                elif line_str.startswith("Total:"):
                    pbar.reset(total=int(line_str.split(":")[1].strip()))
                    process_start = True
                elif line_str.startswith("Finish:"):
                    break
    await process.wait()
    return result
