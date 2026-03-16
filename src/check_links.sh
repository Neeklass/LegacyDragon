root="data/source"
find "$root" -type d | while IFS= read -r d; do
  if ! find "$d" -mindepth 1 -maxdepth 1 -type d | grep -q .; then
    f="$d/links.txt"
    if [[ ! -f "$f" ]]; then
      echo "INVALID | $d | links.txt missing"
    else
      c=$(grep -Eic '^[[:space:]]*(https?://|www\.)' "$f")
      [[ "$c" -eq 2 ]] || echo "INVALID | $d | $c links (expected 2)"
    fi
  fi
done