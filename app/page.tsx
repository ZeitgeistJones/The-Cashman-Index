import IndexApp from "@/components/IndexApp";
import acquisitionFile from "@/data/acquisition_index.json";
import draftFile from "@/data/draft_index.json";
import exitFile from "@/data/exit_resumes.json";
import franchiseFile from "@/data/franchise_index.json";
import gmFile from "@/data/gm_index.json";
import leagueMovesFile from "@/data/league_moves.json";
import seasonFile from "@/data/season_index.json";
import tradeFile from "@/data/trade_index.json";
import yearlyFile from "@/data/yearly_index.json";
import type { MovesFile } from "@/lib/moves";
import type {
  DraftFile,
  ExitFile,
  FranchiseFile,
  GmFile,
  SeasonFile,
  YearlyFile,
} from "@/lib/rankings";

const moves = leagueMovesFile as MovesFile;
const franchises = franchiseFile as FranchiseFile;
const gms = gmFile as GmFile;
const exits = exitFile as ExitFile;
const yearly = yearlyFile as YearlyFile;
const seasonIndex = seasonFile as SeasonFile;
const draft = draftFile as DraftFile;

export default function Home() {
  return (
    <IndexApp
      moves={moves}
      franchises={franchises}
      gms={gms}
      exits={exits}
      yearly={yearly}
      seasonIndex={seasonIndex}
      draft={draft}
      acquisition={acquisitionFile}
      trade={tradeFile}
    />
  );
}
