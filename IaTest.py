def reply_to_mentions():
    user_id = get_user_id()
    if not user_id:
        print("Não foi possível obter o ID do usuário.")
        return

    last_mention_id = get_last_processed_id()
    print(f"Último ID processado: {last_mention_id}")

    try:
        # Busca todas as menções novas
        mentions = client.get_users_mentions(
            id=user_id,
            since_id=last_mention_id,
            max_results=20,  # Aumente esse valor se necessário
            tweet_fields=["id", "author_id", "referenced_tweets"],
        )
        
        if mentions.data:
            print(f"Encontradas {len(mentions.data)} menções.")
            new_last_mention_id = last_mention_id  # Inicializa com o último ID processado

            for mention in mentions.data:
                referenced_tweet_id = None

                # Encontra o ID do tweet original (se for uma resposta)
                if mention.referenced_tweets:
                    for ref in mention.referenced_tweets:
                        if ref["type"] == "replied_to":
                            referenced_tweet_id = ref["id"]
                            break
                
                if not referenced_tweet_id:
                    print(f"Não foi possível encontrar o tweet original para a menção {mention.id}.")
                    continue
                
                # Obtém o tweet original
                original_tweet = client.get_tweet(id=referenced_tweet_id, tweet_fields=["text"]).data
                if not original_tweet:
                    print(f"Não foi possível obter o tweet original {referenced_tweet_id}.")
                    continue
                
                # Gera uma resposta usando o ChatGPT
                print(f"Gerando resposta para o tweet {original_tweet.id}...")
                response_text = generate_chatgpt_response(original_tweet.text)

                # Responde à menção
                try:
                    print(f"Respondendo ao tweet {mention.id}...")
                    client.create_tweet(
                        text=response_text,
                        in_reply_to_tweet_id=mention.id,
                    )
                    print(f"Resposta enviada para o tweet {mention.id}.")
                except Exception as e:
                    print(f"Erro ao responder ao tweet {mention.id}: {e}")
                
                # Atualiza o último ID processado (apenas na memória)
                new_last_mention_id = max(new_last_mention_id, mention.id)

            # Salva o último ID processado no Firebase (após processar todas as menções)
            if new_last_mention_id != last_mention_id:
                save_last_processed_id(new_last_mention_id)
                print(f"Último ID processado atualizado para: {new_last_mention_id}")
        else:
            print("Nenhuma menção nova encontrada.")
    except tweepy.errors.TweepyException as e:
        print(f"Erro ao buscar ou responder menções: {e}")
