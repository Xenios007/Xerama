import { Link, useParams } from "react-router-dom";
import { Card } from "../components/ui/Card";
import { QueryState } from "../components/ui/QueryState";
import { useCharacterCast } from "../api/queries";
import "./CharacterStudioPage.css";

export function CharacterStudioPage() {
  const { seriesId } = useParams<{ seriesId: string }>();
  const cast = useCharacterCast(seriesId);

  return (
    <div>
      <h1>Character Studio</h1>
      <QueryState isLoading={cast.isLoading} error={cast.error}>
        {cast.data && cast.data.characters.length > 0 ? (
          <div className="xr-cast__grid">
            {cast.data.characters.map((character) => (
              <Card key={character.id}>
                <div className="xr-cast__card-header">
                  <Link to={`/characters/${seriesId}/${character.id}`}>
                    <strong>{character.name}</strong>
                  </Link>
                  {character.locked && <span className="xr-badge">locked</span>}
                </div>
                <p className="xr-cast__role">{character.role}</p>
                <p className="xr-cast__desc">{character.description}</p>
              </Card>
            ))}
          </div>
        ) : (
          <p>No cast generated yet for this series.</p>
        )}
      </QueryState>
    </div>
  );
}
