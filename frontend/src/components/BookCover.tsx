const PALETTES = [
  ["#1e6b4a", "#143d2c"],
  ["#c65a2e", "#7c3416"],
  ["#2c5d8a", "#18344f"],
  ["#6d4568", "#3c243c"],
  ["#8d6418", "#4c340b"],
  ["#243044", "#121820"],
];

function hue(title: string) {
  let hash = 0;
  for (let index = 0; index < title.length; index += 1) {
    hash = (hash * 33 + title.charCodeAt(index)) >>> 0;
  }
  return PALETTES[hash % PALETTES.length];
}

export function BookCover({
  title,
  author,
  src,
  large = false,
}: {
  title: string;
  author?: string;
  src?: string | null;
  large?: boolean;
}) {
  if (src) {
    return <img className={large ? "cover cover-lg" : "cover"} src={src} alt={`Capa de ${title}`} />;
  }
  const [from, to] = hue(title);
  return (
    <div className={large ? "cover cover-lg cover-gen" : "cover cover-gen"} style={{ background: `linear-gradient(160deg, ${from}, ${to})` }}>
      <em>{title}</em>
      {author ? <span>{author}</span> : null}
    </div>
  );
}
