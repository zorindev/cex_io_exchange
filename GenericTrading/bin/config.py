'''
Created on Nov 2, 2017

@author: zorindev
'''

# environment
test                    = "off"
db_name                 = "ex"
db_host                 = "zorindev.com"
db_port                 = "3306"

secret                  = "q6SjmqCXma8qJpipJaYpp6XpJY"
db_username             = "66XF09vVqM4="
db_password             = "6JuE3dHWtb3R1J0="  

call_volume_limit       = 10
api_sleep_period        = 1
client_report_period    = 3

price_precision         = 8

# queries
sql_track_call = "insert into calls (timestamp) SELECT  UNIX_TIMESTAMP()"
sql_check_call_limit = "select count(*)  from calls where ((UNIX_TIMESTAMP() - timestamp) < %s)"
sql_get_open_orders_from_db = "select * from orders where state in ('o') and exchange = '%s' and market = '%s' order by last_updated_timestamp asc"

sql_track_new_buy_order = "insert into orders (\
    id, buy_order_number, exchange, market, buy_price, asset_buy_amount, type, state, last_updated_timestamp \
    ) values (UNIX_TIMESTAMP(), %s, '%s', '%s', %s, %s, '%s', '%s', %s)"
    
sql_track_sell_order = "update orders set sell_order_number = %s, sell_price = %s, asset_sell_amount = %s, type = 'sell', state = '%s' where buy_order_number = %s"
    
sql_get_in_progress_order_count = "select count(*) count from orders where exchange = '%s' and market = '%s' and state = 'o'"
sql_get_exchange_config = "select * from ex_config where exchange_name = '%s'"
sql_exchange_markets = "select * from exchange_markets where exchange = '%s' and market = '%s'"
sql_exchange_markets_update = "update exchange_markets set in_use = %s where exchange = '%s' and market = '%s'"

sql_get_open_market_count = "select count(*) as count from exchange_markets where exchange = '%s' and in_use = 1"
sql_get_balance_split_coeficent = "select count(*) as count from exchange_markets where exchange = '%s' and market like '%s' and in_use = 1"
sql_set_order_status = "update orders set state = '%s' where %s = %s"

sql_get_parent_order = "select order_id parent_order from order_relationship where related_order_id = %s and market = '%s' and exchange = '%s'"
sql_get_buy_order_from_sell_order = "select buy_order_number from orders where sell_order_number = %s"
sql_does_relationship_exist = "select * from order_relationship where length(order_id) > 0 and (related_order_id is null or length(related_order_id) = 0) and market = '%s' and exchange = '%s'"
sql_create_order_relationship = "insert into order_relationship (order_id, market, exchange) values (%s, '%s', '%s')"
sql_update_order_relationship = "update order_relationship set related_order_id = %s where order_id = %s and market = '%s' and exchange = '%s' and (related_order_id is null or length(related_order_id) = 0)"
sql_update_order_relationship_undo = "update order_relationship set related_order_id = %s where order_id = %s and related_order_id = %s and market = '%s' and exchange = '%s'"

sql_get_all_related_orders = '''
select t1u1.*
from   orders t1u1
where  t1u1.buy_order_number in (
    select     order_id parent_order_id
        from    order_relationship t2u1 inner join orders t3u1 on (t2u1.order_id = t3u1.buy_order_number) 
        where   t2u1.related_order_id in (%s)
        and     t2u1.market = '%s'
        and     t2u1.exchange = '%s'
)
union all
select t1u2.*
from   orders t1u2
where  t1u2.buy_order_number in (
    select t2u2.related_order_id
      from   order_relationship t2u2 
        where  t2u2.order_id in (
            select    t3u2.order_id parent_order_id
            from      order_relationship t3u2 inner join orders t4u2 on (t3u2.order_id = t4u2.buy_order_number) 
            where     t3u2.related_order_id in (%s)
            and       t3u2.market = '%s'
            and       t3u2.exchange = '%s'
        )
)
'''

sql_find_relationship = '''
    select related_order_id
    from order_relationship 
    where order_id in (

        select order_id 
        from order_relationship 
        where related_order_id = ''
        and market = '%s'
        and exchange = '%s'

    ) and related_order_id != ''
    limit 1;
'''

sql_get_number_of_related_records = "select count(*) count from (" + sql_get_all_related_orders + ") as tbl "

sql_delete_started_order_relationship = "delete from order_relationship where (related_order_id is null or length(related_order_id) = 0) and market = '%s' and exchange = '%s'"


sql_set_unique_nonce = "insert into exchange_nonce values ('%s', %s)"
sql_get_unique_nonce = "select count(*) count from exchange_nonce where exchange = '%s' and nonce = %s"

