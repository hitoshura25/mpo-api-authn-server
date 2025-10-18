interface GenerateWebClientArgs {
    project_path: string;
    framework?: 'vanilla' | 'react' | 'vue';
    server_url?: string;
    client_port?: number;
}
export declare function generateWebClient(args: GenerateWebClientArgs): Promise<{
    content: {
        type: string;
        text: string;
    }[];
    isError?: undefined;
} | {
    content: {
        type: string;
        text: string;
    }[];
    isError: boolean;
}>;
export {};
