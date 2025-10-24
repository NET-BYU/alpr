#!/usr/bin/env python3
"""
Sample Image Downloader
Downloads sample images from https://yavuzceliker.github.io/sample-images/
"""

import os
import argparse
import sys
from pathlib import Path
from urllib.request import urlretrieve
from urllib.error import URLError, HTTPError


def download_images(count, output_folder='images'):
    """
    Download sample images from the web.

    Args:
        count: Number of images to download (1-2000)
        output_folder: Folder to save images to
    """
    if count < 1 or count > 2000:
        print("Error: Count must be between 1 and 2000")
        return False

    # Create output folder if it doesn't exist
    output_path = Path(output_folder)
    output_path.mkdir(exist_ok=True)

    base_url = "https://yavuzceliker.github.io/sample-images/image-{}.jpg"

    print(f"Downloading {count} images to '{output_folder}' folder...")
    successful = 0
    failed = 0

    for i in range(1, count + 1):
        url = base_url.format(i)
        output_file = output_path / f"sample_{i}.jpg"

        try:
            print(f"Downloading image {i}/{count}...", end='\r')
            urlretrieve(url, output_file)
            successful += 1
        except (URLError, HTTPError) as e:
            failed += 1
            print(f"\nWarning: Failed to download image {i}: {e}")
        except Exception as e:
            failed += 1
            print(f"\nError downloading image {i}: {e}")

    print(f"\n\nDownload complete!")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {successful + failed}")

    return True


def clear_images(output_folder='images'):
    """
    Clear all images from the output folder.

    Args:
        output_folder: Folder to clear images from
    """
    output_path = Path(output_folder)

    if not output_path.exists():
        print(f"Folder '{output_folder}' does not exist. Nothing to clear.")
        return

    # Find all sample_*.jpg files
    image_files = list(output_path.glob('sample_*.jpg'))

    if not image_files:
        print(f"No sample images found in '{output_folder}' folder.")
        return

    print(f"Found {len(image_files)} sample images in '{output_folder}' folder.")

    # Confirm deletion
    response = input(
        "Are you sure you want to delete all sample images? (yes/no): ")

    if response.lower() in ['yes', 'y']:
        deleted = 0
        for image_file in image_files:
            try:
                image_file.unlink()
                deleted += 1
            except Exception as e:
                print(f"Error deleting {image_file.name}: {e}")

        print(f"Deleted {deleted} sample images.")
    else:
        print("Deletion cancelled.")


def main():
    parser = argparse.ArgumentParser(
        description='Download or clear sample images from yavuzceliker.github.io',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --download 10          # Download 10 sample images
  %(prog)s --download 50 --folder ./my_images  # Download 50 images to custom folder
  %(prog)s --clear                # Clear all sample images
  %(prog)s --clear --folder ./my_images  # Clear images from custom folder
        """
    )

    parser.add_argument(
        '--download',
        type=int,
        metavar='COUNT',
        help='Download COUNT images (1-2000)'
    )

    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear all sample images from the folder'
    )

    parser.add_argument(
        '--folder',
        type=str,
        default='images',
        help='Output folder for images (default: images)'
    )

    args = parser.parse_args()

    # Check that at least one action is specified
    if not args.download and not args.clear:
        parser.print_help()
        print("\nError: You must specify either --download or --clear")
        sys.exit(1)

    # Execute requested action(s)
    if args.clear:
        clear_images(args.folder)

    if args.download:
        download_images(args.download, args.folder)


if __name__ == '__main__':
    main()
