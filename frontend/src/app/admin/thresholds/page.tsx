"use client";

import React, { useState } from "react";
import { useDemoStore } from "@/store/useDemoStore";
import {
  useActivateThreshold,
  useAdminThresholds,
  useCreateThreshold,
} from "@/hooks/useAdmin";
import { ThresholdConfigResponse, ThresholdCreatePayload } from "@/types";
import { formatDateTime, formatScore } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertCircle,
  CheckCircle2,
  Info,
  Plus,
  RefreshCw,
  Shield,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";

export default function AdminThresholdsPage() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  const { data: thresholds = [], isLoading, error, refetch, isFetching } = useAdminThresholds();
  const activateMutation = useActivateThreshold();
  const createMutation = useCreateThreshold();

  // Create Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newVersionTag, setNewVersionTag] = useState("");
  const [newThresholdValue, setNewThresholdValue] = useState("0.405898");
  const [newDataset, setNewDataset] = useState("LibriSpeech dev-clean");
  const [newCriterion, setNewCriterion] = useState("equal_error_rate_minimization");
  const [newModel, setNewModel] = useState("speechbrain/spkrec-ecapa-voxceleb");
  const [newEerPercent, setNewEerPercent] = useState("1.25");

  // Activate Modal State
  const [activateTarget, setActivateTarget] = useState<ThresholdConfigResponse | null>(null);
  const [isActivateOpen, setIsActivateOpen] = useState(false);

  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const activeConfig = thresholds.find((t) => t.is_active);

  const handleOpenActivateDialog = (item: ThresholdConfigResponse) => {
    setActionError(null);
    setActionSuccess(null);
    setActivateTarget(item);
    setIsActivateOpen(true);
  };

  const handleConfirmActivation = async () => {
    if (!activateTarget) return;
    setActionError(null);
    try {
      await activateMutation.mutateAsync(activateTarget.id);
      setActionSuccess(`Threshold version ${activateTarget.version_tag} is now active.`);
      setIsActivateOpen(false);
    } catch (err: any) {
      setActionError(err.response?.data?.message || err.message || "Failed to activate threshold.");
    }
  };

  const handleCreateThresholdSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);

    const val = parseFloat(newThresholdValue);
    if (isNaN(val) || val < -1.0 || val > 1.0) {
      setActionError("Threshold value must be a valid cosine similarity score between -1.0 and +1.0.");
      return;
    }

    const eerVal = parseFloat(newEerPercent);
    const metadata = isNaN(eerVal) ? {} : { eer: eerVal / 100.0, empirical_eer_percent: eerVal };

    const payload: ThresholdCreatePayload = {
      version_tag: newVersionTag.trim(),
      model_identifier: newModel.trim(),
      threshold_value: val,
      calibration_dataset: newDataset.trim(),
      calibration_criterion: newCriterion.trim(),
      calibration_metadata: metadata,
      is_active: false,
    };

    try {
      await createMutation.mutateAsync(payload);
      setActionSuccess(`Calibrated threshold ${newVersionTag} registered successfully.`);
      setIsCreateOpen(false);
      setNewVersionTag("");
    } catch (err: any) {
      setActionError(err.response?.data?.message || err.message || "Failed to create threshold configuration.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Threshold Governance & Provenance</h1>
            {isDemoMode && (
              <Badge variant="warning" className="gap-1 text-[10px]">
                <Sparkles className="w-3 h-3" /> DEMO
              </Badge>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Dynamic decision boundaries loaded at runtime by the speaker verification engine.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => refetch()}
            disabled={isFetching}
            className="gap-1.5 text-xs border-slate-700 bg-slate-900/60"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-blue-400 ${isFetching ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </Button>

          <Button
            size="sm"
            onClick={() => setIsCreateOpen(true)}
            className="bg-blue-600 hover:bg-blue-500 text-white gap-1.5 text-xs font-semibold"
          >
            <Plus className="w-4 h-4" />
            <span>Register Threshold</span>
          </Button>
        </div>
      </div>

      {/* Notifications */}
      {actionSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-xs text-emerald-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>{actionSuccess}</span>
          </div>
          <Button size="sm" variant="ghost" onClick={() => setActionSuccess(null)} className="h-6 text-xs text-slate-400">
            Dismiss
          </Button>
        </div>
      )}

      {actionError && (
        <div className="p-3.5 rounded-xl bg-red-950/40 border border-red-800/60 text-xs text-red-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400" />
            <span>{actionError}</span>
          </div>
          <Button size="sm" variant="ghost" onClick={() => setActionError(null)} className="h-6 text-xs text-slate-400">
            Dismiss
          </Button>
        </div>
      )}

      {/* Active Threshold Overview Card */}
      {activeConfig && (
        <Card className="border-emerald-600/50 bg-gradient-to-r from-slate-900 via-slate-900 to-emerald-950/30">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div className="space-y-1">
              <span className="text-[11px] uppercase font-mono tracking-wider text-emerald-400 font-semibold flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5" />
                Active Operational Decision Boundary
              </span>
              <CardTitle className="text-xl font-bold text-white font-mono">
                {activeConfig.version_tag}
              </CardTitle>
            </div>
            <Badge variant="success" className="text-xs">
              ACTIVE ENFORCEMENT
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs pt-2">
              <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1">
                <span className="text-slate-400">Operating Cosine Threshold</span>
                <p className="font-mono text-emerald-400 text-lg font-bold">
                  {formatScore(activeConfig.threshold_value, 6)}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1">
                <span className="text-slate-400">Model Identifier</span>
                <p className="font-mono text-blue-300 text-xs font-semibold truncate">
                  {activeConfig.model_identifier}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1">
                <span className="text-slate-400">Calibration Dataset</span>
                <p className="text-white text-xs font-medium">
                  {activeConfig.calibration_dataset}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1">
                <span className="text-slate-400">Activated Timestamp</span>
                <p className="text-slate-300 text-xs font-mono">
                  {formatDateTime(activeConfig.updated_at)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Governance Architecture Notice */}
      <div className="p-4 rounded-xl bg-blue-950/40 border border-blue-800/60 text-xs text-blue-200 flex items-start gap-3">
        <Info className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <strong className="text-white">Zero Hardcoded Thresholds Guarantee:</strong>
          <p className="text-slate-300 leading-relaxed">
            Every verification query resolves the active threshold configuration directly from PostgreSQL. Activating a threshold deactivates all other boundaries for that model, providing instant security adjustments without application restarts.
          </p>
        </div>
      </div>

      {/* Registered Thresholds Table */}
      <Card className="border-slate-800 bg-slate-900/80">
        <CardHeader>
          <CardTitle className="text-base font-semibold text-white">Registered Decision Boundaries</CardTitle>
          <CardDescription className="text-xs text-slate-400">
            Database table: <code className="font-mono text-blue-300">threshold_configurations</code>
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Version Tag</TableHead>
                <TableHead>Model Backbone</TableHead>
                <TableHead>Threshold (Cosine)</TableHead>
                <TableHead>Calibration Dataset</TableHead>
                <TableHead>Criterion</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created At</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-10 text-xs text-slate-500">
                    Loading registered threshold configurations...
                  </TableCell>
                </TableRow>
              ) : thresholds.length > 0 ? (
                thresholds.map((item) => (
                  <TableRow key={item.id} className="hover:bg-slate-800/40">
                    <TableCell className="font-mono text-xs font-semibold text-white">
                      {item.version_tag}
                    </TableCell>

                    <TableCell className="font-mono text-xs text-slate-400 truncate max-w-[160px]">
                      {item.model_identifier}
                    </TableCell>

                    <TableCell className="font-mono text-xs font-bold text-emerald-400">
                      {formatScore(item.threshold_value, 6)}
                    </TableCell>

                    <TableCell className="text-xs text-slate-300">
                      {item.calibration_dataset}
                    </TableCell>

                    <TableCell className="text-[11px] text-slate-400 font-mono">
                      {item.calibration_criterion}
                    </TableCell>

                    <TableCell>
                      {item.is_active ? (
                        <Badge variant="success" className="text-[10px] gap-1">
                          <CheckCircle2 className="w-3 h-3" /> ACTIVE
                        </Badge>
                      ) : (
                        <Badge variant="secondary" className="text-[10px]">
                          INACTIVE
                        </Badge>
                      )}
                    </TableCell>

                    <TableCell className="text-xs text-slate-400 font-mono">
                      {formatDateTime(item.created_at)}
                    </TableCell>

                    <TableCell className="text-right">
                      {!item.is_active ? (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleOpenActivateDialog(item)}
                          className="text-xs h-7 px-2.5 text-blue-400 hover:text-blue-300 border-slate-700 gap-1"
                        >
                          <Zap className="w-3 h-3" />
                          <span>Activate</span>
                        </Button>
                      ) : (
                        <span className="text-[11px] text-emerald-400 font-medium">Currently Active</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-10 text-xs text-slate-500">
                    No threshold configurations found in PostgreSQL.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Register Threshold Modal */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="max-w-md bg-slate-900 border-slate-800 text-slate-100">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <Plus className="w-5 h-5 text-blue-400" />
              <span>Register Calibrated Threshold</span>
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-400">
              Provide provenance and empirical evaluation results for the decision boundary.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateThresholdSubmit} className="space-y-3.5 text-xs">
            <div className="space-y-1">
              <label className="text-slate-300 font-medium">Version Tag</label>
              <Input
                placeholder="e.g. voxceleb-eer-v2.0"
                value={newVersionTag}
                onChange={(e) => setNewVersionTag(e.target.value)}
                required
                className="text-xs h-8 bg-slate-950 border-slate-700"
              />
            </div>

            <div className="space-y-1">
              <label className="text-slate-300 font-medium">Operating Threshold Value (Cosine)</label>
              <Input
                placeholder="e.g. 0.405898"
                value={newThresholdValue}
                onChange={(e) => setNewThresholdValue(e.target.value)}
                required
                className="text-xs h-8 bg-slate-950 border-slate-700 font-mono"
              />
            </div>

            <div className="space-y-1">
              <label className="text-slate-300 font-medium">Calibration Dataset Provenance</label>
              <Input
                placeholder="e.g. LibriSpeech dev-clean"
                value={newDataset}
                onChange={(e) => setNewDataset(e.target.value)}
                required
                className="text-xs h-8 bg-slate-950 border-slate-700"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-slate-300 font-medium">Empirical EER (%)</label>
                <Input
                  placeholder="e.g. 1.25"
                  value={newEerPercent}
                  onChange={(e) => setNewEerPercent(e.target.value)}
                  className="text-xs h-8 bg-slate-950 border-slate-700 font-mono"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-300 font-medium">Neural Backbone</label>
                <Input
                  value={newModel}
                  onChange={(e) => setNewModel(e.target.value)}
                  className="text-xs h-8 bg-slate-950 border-slate-700 font-mono"
                />
              </div>
            </div>

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsCreateOpen(false)}
                className="text-xs"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                isLoading={createMutation.isPending}
                className="bg-blue-600 hover:bg-blue-500 text-white text-xs"
              >
                Save Threshold
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Activate Confirmation Modal */}
      <Dialog open={isActivateOpen} onOpenChange={setIsActivateOpen}>
        <DialogContent className="max-w-md bg-slate-900 border-slate-800 text-slate-100">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-emerald-400" />
              <span>Confirm Operating Boundary Activation</span>
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-400">
              Activate <strong className="text-white">{activateTarget?.version_tag}</strong> (Cosine: {activateTarget?.threshold_value}).
            </DialogDescription>
          </DialogHeader>

          <div className="p-3.5 rounded-lg bg-emerald-950/30 border border-emerald-800/50 text-xs text-emerald-200 space-y-1">
            <p>
              Activating this threshold will immediately apply it to all incoming 1:1 speaker verification assessments. The previous active threshold for <code className="font-mono text-white">{activateTarget?.model_identifier}</code> will be retired.
            </p>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsActivateOpen(false)}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleConfirmActivation}
              isLoading={activateMutation.isPending}
              className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs gap-1.5"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Confirm Activation</span>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
