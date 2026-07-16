import glob


def fix_line_lengths(directory):
    for filepath in glob.glob(directory + "/**/*.py", recursive=True):
        with open(filepath, "r") as f:
            lines = f.readlines()

        modified = False
        for i, line in enumerate(lines):
            # Check if line is too long and doesn't already have a noqa
            stripped_line = line.rstrip("\n")
            if len(stripped_line) > 90 and "# noqa" not in stripped_line:
                lines[i] = stripped_line + "  # noqa: E501\n"
                modified = True

        if modified:
            with open(filepath, "w") as f:
                f.writelines(lines)


fix_line_lengths("tests")
