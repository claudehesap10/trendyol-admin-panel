import { Octokit } from "@octokit/rest";

export class GitHubService {
  private octokit: Octokit;

  constructor(token: string) {
    this.octokit = new Octokit({ auth: token });
  }

  /**
   * Workflow'u manuel olarak tetikle
   */
  async triggerWorkflow(owner: string, repo: string, workflowId: string, ref: string = "main") {
    try {
      const response = await this.octokit.actions.createWorkflowDispatch({
        owner,
        repo,
        workflow_id: workflowId,
        ref,
      });
      return { success: true, status: response.status };
    } catch (error) {
      throw new Error(`Failed to trigger workflow: ${error}`);
    }
  }

  /**
   * Workflow run'ın durumunu sorgula
   */
  async getWorkflowRunStatus(owner: string, repo: string, runId: number) {
    try {
      const response = await this.octokit.actions.getWorkflowRun({
        owner,
        repo,
        run_id: runId,
      });
      return {
        id: response.data.id,
        status: response.data.status,
        conclusion: response.data.conclusion,
        createdAt: response.data.created_at,
        updatedAt: response.data.updated_at,
        name: response.data.name,
      };
    } catch (error) {
      throw new Error(`Failed to get workflow run status: ${error}`);
    }
  }

  /**
   * Son workflow run'ları listele
   */
  async getWorkflowRuns(owner: string, repo: string, workflowId: string, limit: number = 10) {
    try {
      const response = await this.octokit.actions.listWorkflowRuns({
        owner,
        repo,
        workflow_id: workflowId,
        per_page: limit,
      });
      return response.data.workflow_runs.map((run: any) => ({
        id: run.id,
        status: run.status,
        conclusion: run.conclusion,
        createdAt: run.created_at,
        updatedAt: run.updated_at,
        name: run.name,
      }));
    } catch (error) {
      throw new Error(`Failed to list workflow runs: ${error}`);
    }
  }

  /**
   * Workflow run'ın artifact'larını listele (Excel raporları)
   */
  async getWorkflowArtifacts(owner: string, repo: string, runId: number) {
    try {
      const response = await this.octokit.actions.listWorkflowRunArtifacts({
        owner,
        repo,
        run_id: runId,
      });
      return response.data.artifacts.map((artifact: any) => ({
        id: artifact.id,
        name: artifact.name,
        sizeInBytes: artifact.size_in_bytes,
        createdAt: artifact.created_at,
        expiresAt: artifact.expires_at,
      }));
    } catch (error) {
      throw new Error(`Failed to list workflow artifacts: ${error}`);
    }
  }

  /**
   * Artifact'ın download URL'sini al
   */
  async getArtifactDownloadUrl(owner: string, repo: string, artifactId: number) {
    try {
      const response = await this.octokit.actions.downloadArtifact({
        owner,
        repo,
        artifact_id: artifactId,
        archive_format: "zip",
      });
      return response.url;
    } catch (error) {
      throw new Error(`Failed to get artifact download URL: ${error}`);
    }
  }
}
