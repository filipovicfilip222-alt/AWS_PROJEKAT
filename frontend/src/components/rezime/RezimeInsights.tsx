import { AlertTriangle, Lightbulb, TrendingDown } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { RezimeInsights } from "@/api/rezime";

export interface RezimeInsightsProps {
  insights: RezimeInsights;
}

export function RezimeInsightsView({ insights }: RezimeInsightsProps) {
  const summary = insights.summary;
  const top = insights.topProblematic ?? [];
  const tags = insights.tagPatterns ?? [];
  const preporuke = insights.preporukeZaSledeceKonsultacije ?? [];
  const bezFb = insights.bezFeedbackUpozorenje ?? [];

  return (
    <div className="space-y-4">
      {summary && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Pregled</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <Stat label="Pitanja" value={summary.totalQuestions} />
            <Stat label="Feedback" value={summary.totalFeedback} />
            <Stat label='Prosečno "Jasno"' value={`${summary.averageJasno}%`} />
            <Stat label="Bez feedback-a" value={summary.questionsWithoutFeedback} />
          </CardContent>
        </Card>
      )}

      {top.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingDown className="h-4 w-4" /> Top problematična pitanja
            </CardTitle>
            <CardDescription>
              Pitanja sa najnižim procentom razumevanja (i bar 3 glasa)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {top.map((t) => (
              <div
                key={t.questionId}
                className="border rounded-md p-3 space-y-1"
              >
                <div className="flex justify-between items-start gap-2">
                  <p className="font-medium text-sm">
                    #{t.rank} {t.pitanje}
                  </p>
                  <Badge variant="warning">
                    {t.percentJasno}% / {t.totalFeedback} glasova
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">{t.preporuka}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {tags.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Pattern po tagovima</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {tags.map((t) => (
              <div key={t.tag} className="border rounded-md p-3 space-y-1">
                <div className="flex justify-between items-start gap-2">
                  <Badge variant="secondary">{t.tag}</Badge>
                  <span className="text-sm">
                    {t.questionCount} pitanja · {t.averageJasno}%
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">{t.interpretation}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {preporuke.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Lightbulb className="h-4 w-4" /> Preporuke za sledeće konsultacije
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc pl-5 space-y-1 text-sm">
              {preporuke.map((p, i) => (
                <li key={i}>{p}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {bezFb.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" /> Pitanja bez feedback-a
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {bezFb.map((b) => (
              <div key={b.questionId} className="border rounded-md p-3">
                <p className="font-medium">{b.pitanje}</p>
                <p className="text-muted-foreground text-xs mt-1">{b.razlog}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="space-y-1">
      <div className="text-xs uppercase text-muted-foreground tracking-wide">{label}</div>
      <div className="text-2xl font-semibold">{value}</div>
    </div>
  );
}
