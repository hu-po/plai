import os
import asyncio
from datetime import timedelta

async def scrape_directory_for_file(
    directory: str, 
    filename: str, 
    callback: callable, 
    interval: timedelta = timedelta(seconds=3), 
    timeout: timedelta = timedelta(minutes=1)
):
    try:
        async def _scrape():
            while True:
                if filename in os.listdir(directory):
                    full_path = os.path.join(directory, filename)
                    if asyncio.iscoroutinefunction(callback):
                        await callback(full_path)
                    else:
                        callback(full_path)
                await asyncio.sleep(interval.total_seconds())
        
        await asyncio.wait_for(_scrape(), timeout=timeout.total_seconds())
    except asyncio.TimeoutError:
        print("Timeout reached. Stopping the function.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# Example usage with an asynchronous callback:
# async def async_print_path(path):
#     await asyncio.sleep(1)  # Just simulating some async operation here.
#     print(f"File found at: {path}")
# asyncio.run(scrape_directory_for_file('.', 'myfile.txt', async_print_path))
