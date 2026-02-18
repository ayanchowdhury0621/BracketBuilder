import { createBrowserRouter } from "react-router";
import { Layout } from "./components/Layout";
import { HomeScreen } from "./components/HomeScreen";
import { BracketScreen } from "./components/BracketScreen";
import { MatchupScreen } from "./components/MatchupScreen";
import { AnalysisScreen } from "./components/AnalysisScreen";
import { RotoBotScreen } from "./components/RotoBotScreen";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Layout,
    children: [
      { index: true, Component: HomeScreen },
      { path: "bracket", Component: BracketScreen },
      { path: "matchup/:id", Component: MatchupScreen },
      { path: "analysis", Component: AnalysisScreen },
      { path: "rotobot", Component: RotoBotScreen },
    ],
  },
]);
