--
-- PostgreSQL database dump
--

\restrict Bwp2KQ7FmAe57dUa4BwAwDZLLjCbkccKoR46iA7vR182ShuVdoIdmup3MlfqlKe

-- Dumped from database version 16.11 (Debian 16.11-1.pgdg12+1)
-- Dumped by pg_dump version 16.11 (Debian 16.11-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: devmatrix; Type: SCHEMA; Schema: -; Owner: devmatrix
--

CREATE SCHEMA devmatrix;


ALTER SCHEMA devmatrix OWNER TO devmatrix;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: devmatrix; Owner: devmatrix
--

CREATE FUNCTION devmatrix.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION devmatrix.update_updated_at_column() OWNER TO devmatrix;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agent_decisions; Type: TABLE; Schema: devmatrix; Owner: devmatrix
--

CREATE TABLE devmatrix.agent_decisions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    task_id uuid,
    decision_type character varying(100) NOT NULL,
    reasoning text,
    approved boolean,
    feedback text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    decided_at timestamp without time zone,
    metadata jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE devmatrix.agent_decisions OWNER TO devmatrix;

--
-- Name: cost_tracking; Type: TABLE; Schema: devmatrix; Owner: devmatrix
--

CREATE TABLE devmatrix.cost_tracking (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    task_id uuid,
    model_name character varying(100) NOT NULL,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    total_cost_usd numeric(10,6) DEFAULT 0 NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE devmatrix.cost_tracking OWNER TO devmatrix;

--
-- Name: git_commits; Type: TABLE; Schema: devmatrix; Owner: devmatrix
--

CREATE TABLE devmatrix.git_commits (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    task_id uuid,
    commit_hash character varying(40) NOT NULL,
    commit_message text NOT NULL,
    files_changed jsonb DEFAULT '[]'::jsonb,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE devmatrix.git_commits OWNER TO devmatrix;

--
-- Name: projects; Type: TABLE; Schema: devmatrix; Owner: devmatrix
--

CREATE TABLE devmatrix.projects (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    status character varying(50) DEFAULT 'pending'::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT valid_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'in_progress'::character varying, 'completed'::character varying, 'failed'::character varying, 'cancelled'::character varying])::text[])))
);


ALTER TABLE devmatrix.projects OWNER TO devmatrix;

--
-- Name: tasks; Type: TABLE; Schema: devmatrix; Owner: devmatrix
--

CREATE TABLE devmatrix.tasks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid,
    agent_name character varying(100) NOT NULL,
    task_type character varying(100) NOT NULL,
    input text,
    output text,
    status character varying(50) DEFAULT 'pending'::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    metadata jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT valid_task_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'in_progress'::character varying, 'completed'::character varying, 'failed'::character varying, 'cancelled'::character varying])::text[])))
);


ALTER TABLE devmatrix.tasks OWNER TO devmatrix;

--
-- Data for Name: agent_decisions; Type: TABLE DATA; Schema: devmatrix; Owner: devmatrix
--

COPY devmatrix.agent_decisions (id, task_id, decision_type, reasoning, approved, feedback, created_at, decided_at, metadata) FROM stdin;
\.


--
-- Data for Name: cost_tracking; Type: TABLE DATA; Schema: devmatrix; Owner: devmatrix
--

COPY devmatrix.cost_tracking (id, task_id, model_name, input_tokens, output_tokens, total_cost_usd, created_at, metadata) FROM stdin;
\.


--
-- Data for Name: git_commits; Type: TABLE DATA; Schema: devmatrix; Owner: devmatrix
--

COPY devmatrix.git_commits (id, task_id, commit_hash, commit_message, files_changed, created_at, metadata) FROM stdin;
\.


--
-- Data for Name: projects; Type: TABLE DATA; Schema: devmatrix; Owner: devmatrix
--

COPY devmatrix.projects (id, name, description, status, created_at, updated_at, metadata) FROM stdin;
\.


--
-- Data for Name: tasks; Type: TABLE DATA; Schema: devmatrix; Owner: devmatrix
--

COPY devmatrix.tasks (id, project_id, agent_name, task_type, input, output, status, created_at, started_at, completed_at, metadata) FROM stdin;
\.


--
-- Name: agent_decisions agent_decisions_pkey; Type: CONSTRAINT; Schema: devmatrix; Owner: devmatrix
--

ALTER TABLE ONLY devmatrix.agent_decisions
    ADD CONSTRAINT agent_decisions_pkey PRIMARY KEY (id);


--
-- Name: cost_tracking cost_tracking_pkey; Type: CONSTRAINT; Schema: devmatrix; Owner: devmatrix
--

ALTER TABLE ONLY devmatrix.cost_tracking
    ADD CONSTRAINT cost_tracking_pkey PRIMARY KEY (id);


--
-- Name: git_commits git_commits_pkey; Type: CONSTRAINT; Schema: devmatrix; Owner: devmatrix
--

ALTER TABLE ONLY devmatrix.git_commits
    ADD CONSTRAINT git_commits_pkey PRIMARY KEY (id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: devmatrix; Owner: devmatrix
--

ALTER TABLE ONLY devmatrix.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: devmatrix; Owner: devmatrix
--

ALTER TABLE ONLY devmatrix.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- Name: idx_commits_hash; Type: INDEX; Schema: devmatrix; Owner: devmatrix
--

CREATE INDEX idx_commits_hash ON devmatrix.git_commits USING btree (commit_hash);


--
-- Name: idx_commits_task_id; Type: INDEX; Schema: devmatrix; Owner: devmatrix
--

CREATE INDEX idx_commits_task_id ON devmatrix.git_commits USING btree (task_id);


--
-- Name: idx_cost_created_at; Type: INDEX; Schema: devmatrix; Owner: devmatrix
--

CREATE INDEX idx_cost_created_at ON devmatrix.cost_tracking USING btree (created_at DESC);


--
-- Name: idx_cost_model; Type: INDEX; Schema: devmatrix; Owner: devmatrix
--

CREATE INDEX idx_cost_model ON devmatrix.cost_tracking USING btree (model_name);


--
-- Name: idx_cost_task_id; Type: INDEX; Schema: devmatrix; Owner: devmatrix
--

CREATE INDEX idx_cost_task_id ON devmatrix.cost_tracking USING btree (task_id);


--
-- Name: idx_decisions_approved; Type: INDEX; Schema: devmatrix; Owner: devmatrix
--

CREATE INDEX idx_decisions_approved ON devmatrix.agent_decisions USING btree (approved);


--
-- Name: idx_decisions_task_id; Type: INDEX; Schema: devmatrix; Owner: devmatrix
--

CREATE INDEX idx_decisions_task_id ON devmatrix.agent_decisions USING btree (task_id);


--
-- Name: idx_projects_created_at; Type: INDEX; Schema: devmatrix; Owner: devmatrix
--

CREATE INDEX idx_projects_created_at ON devmatrix.projects USING btree (created_at DESC);


--
-- Name: idx_projects_status; Type: INDEX; Schema: devmatrix; Owner: devmatrix
--

CREATE INDEX idx_projects_status ON devmatrix.projects USING btree (status);


--
-- Name: idx_tasks_agent_name; Type: INDEX; Schema: devmatrix; Owner: devmatrix
--

CREATE INDEX idx_tasks_agent_name ON devmatrix.tasks USING btree (agent_name);


--
-- Name: idx_tasks_created_at; Type: INDEX; Schema: devmatrix; Owner: devmatrix
--

CREATE INDEX idx_tasks_created_at ON devmatrix.tasks USING btree (created_at DESC);


--
-- Name: idx_tasks_project_id; Type: INDEX; Schema: devmatrix; Owner: devmatrix
--

CREATE INDEX idx_tasks_project_id ON devmatrix.tasks USING btree (project_id);


--
-- Name: idx_tasks_status; Type: INDEX; Schema: devmatrix; Owner: devmatrix
--

CREATE INDEX idx_tasks_status ON devmatrix.tasks USING btree (status);


--
-- Name: projects update_projects_updated_at; Type: TRIGGER; Schema: devmatrix; Owner: devmatrix
--

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON devmatrix.projects FOR EACH ROW EXECUTE FUNCTION devmatrix.update_updated_at_column();


--
-- Name: agent_decisions agent_decisions_task_id_fkey; Type: FK CONSTRAINT; Schema: devmatrix; Owner: devmatrix
--

ALTER TABLE ONLY devmatrix.agent_decisions
    ADD CONSTRAINT agent_decisions_task_id_fkey FOREIGN KEY (task_id) REFERENCES devmatrix.tasks(id) ON DELETE CASCADE;


--
-- Name: cost_tracking cost_tracking_task_id_fkey; Type: FK CONSTRAINT; Schema: devmatrix; Owner: devmatrix
--

ALTER TABLE ONLY devmatrix.cost_tracking
    ADD CONSTRAINT cost_tracking_task_id_fkey FOREIGN KEY (task_id) REFERENCES devmatrix.tasks(id) ON DELETE SET NULL;


--
-- Name: git_commits git_commits_task_id_fkey; Type: FK CONSTRAINT; Schema: devmatrix; Owner: devmatrix
--

ALTER TABLE ONLY devmatrix.git_commits
    ADD CONSTRAINT git_commits_task_id_fkey FOREIGN KEY (task_id) REFERENCES devmatrix.tasks(id) ON DELETE SET NULL;


--
-- Name: tasks tasks_project_id_fkey; Type: FK CONSTRAINT; Schema: devmatrix; Owner: devmatrix
--

ALTER TABLE ONLY devmatrix.tasks
    ADD CONSTRAINT tasks_project_id_fkey FOREIGN KEY (project_id) REFERENCES devmatrix.projects(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict Bwp2KQ7FmAe57dUa4BwAwDZLLjCbkccKoR46iA7vR182ShuVdoIdmup3MlfqlKe

